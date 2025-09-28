import random
import time
from threading import Thread, Event
from flask import current_app
from app.models import Draw, Participant, Winner, db
from datetime import datetime

class DrawEngine:
    def __init__(self):
        self.current_draw = None
        self.is_running = False
        self.current_winner = None
        self.winners_drawn = 0
        self.total_winners = 0
        self.animation_event = Event()
        self.animation_thread = None
    
    def start_draw(self, draw_id):
        try:
            # Use a new session for this operation
            draw = Draw.query.get(draw_id)
            if not draw:
                return False, "Draw not found"
            
            participants = Participant.query.filter_by(draw_id=draw_id, is_verified=True).all()
            if len(participants) < draw.number_of_winners:
                return False, f"Not enough participants. Need {draw.number_of_winners}, have {len(participants)}"
            
            # Store only the necessary data, not the entire ORM object
            self.current_draw = {
                'id': draw.id,
                'name': draw.name,
                'prize_amount': draw.prize_amount,
                'number_of_winners': draw.number_of_winners,
                'status': draw.status
            }
            
            self.is_running = True
            self.winners_drawn = 0
            self.total_winners = draw.number_of_winners
            self.participants = [p.phone_number for p in participants]
            self.participant_objects = participants  # Keep for winner selection
            
            # Update draw status in database
            draw.status = 'active'
            db.session.commit()
            
            return True, "Draw started successfully"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error starting draw: {e}")
            return False, f"Error starting draw: {str(e)}"
    
    def stop_draw(self):
        try:
            self.is_running = False
            self.animation_event.set()
            
            if self.current_draw:
                # Update draw status in database
                draw = Draw.query.get(self.current_draw['id'])
                if draw:
                    draw.status = 'completed'
                    db.session.commit()
            
            return True, "Draw stopped"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error stopping draw: {e}")
            return False, f"Error stopping draw: {str(e)}"
    
    def draw_next_winner(self):
        if not self.is_running or self.winners_drawn >= self.total_winners:
            return None
        
        try:
            # Get fresh data from database to avoid detached instance issues
            draw = Draw.query.get(self.current_draw['id'])
            if not draw:
                return None
            
            # Get participants who haven't won yet
            winner_participants = Participant.query.filter(
                Participant.draw_id == self.current_draw['id'],
                Participant.is_verified == True
            ).filter(
                ~Participant.id.in_(
                    db.session.query(Winner.participant_id).filter(
                        Winner.draw_id == self.current_draw['id']
                    )
                )
            ).all()
            
            if not winner_participants:
                return None
            
            # Select random winner
            winner = random.choice(winner_participants)
            self.winners_drawn += 1
            
            # Save winner to database
            new_winner = Winner(
                draw_id=self.current_draw['id'],
                participant_id=winner.id,
                position=self.winners_drawn
            )
            db.session.add(new_winner)
            
            # Update draw status if all winners drawn
            if self.winners_drawn >= self.total_winners:
                draw.status = 'completed'
                draw.completed_at = datetime.utcnow()
                self.is_running = False
            
            db.session.commit()
            
            return {
                'phone_number': winner.phone_number,
                'position': self.winners_drawn,
                'total_winners': self.total_winners,
                'draw_complete': self.winners_drawn >= self.total_winners
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error drawing winner: {e}")
            return None
    
    def get_animation_sequence(self, duration=5):
        """Generate animation sequence for the draw display"""
        if not self.is_running:
            return []
        
        try:
            # Get fresh participant data
            participants = Participant.query.filter(
                Participant.draw_id == self.current_draw['id'],
                Participant.is_verified == True
            ).filter(
                ~Participant.id.in_(
                    db.session.query(Winner.participant_id).filter(
                        Winner.draw_id == self.current_draw['id']
                    )
                )
            ).all()
            
            sequence = []
            start_time = time.time()
            
            while time.time() - start_time < duration and participants:
                random_phone = random.choice(participants).phone_number
                sequence.append({
                    'phone_number': random_phone,
                    'timestamp': time.time()
                })
                time.sleep(0.1)  # Fast animation
            
            return sequence
            
        except Exception as e:
            current_app.logger.error(f"Error generating animation: {e}")
            return []

# Global draw engine instance
draw_engine = DrawEngine()