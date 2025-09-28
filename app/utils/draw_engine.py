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
        draw = Draw.query.get(draw_id)
        if not draw:
            return False, "Draw not found"
        
        participants = Participant.query.filter_by(draw_id=draw_id, is_verified=True).all()
        if len(participants) < draw.number_of_winners:
            return False, f"Not enough participants. Need {draw.number_of_winners}, have {len(participants)}"
        
        self.current_draw = draw
        self.is_running = True
        self.winners_drawn = 0
        self.total_winners = draw.number_of_winners
        self.participants = participants
        
        # Update draw status
        draw.status = 'active'
        db.session.commit()
        
        return True, "Draw started successfully"
    
    def stop_draw(self):
        self.is_running = False
        self.animation_event.set()
        
        if self.current_draw:
            draw = Draw.query.get(self.current_draw.id)
            draw.status = 'completed'
            db.session.commit()
        
        return True, "Draw stopped"
    
    def draw_next_winner(self):
        if not self.is_running or self.winners_drawn >= self.total_winners:
            return None
        
        # Remove already selected winners from pool
        available_participants = [p for p in self.participants 
                                if not any(w.participant_id == p.id for w in self.current_draw.winners)]
        
        if not available_participants:
            return None
        
        # Select random winner
        winner = random.choice(available_participants)
        self.winners_drawn += 1
        
        # Save winner to database
        new_winner = Winner(
            draw_id=self.current_draw.id,
            participant_id=winner.id,
            position=self.winners_drawn
        )
        db.session.add(new_winner)
        
        # Update draw status if all winners drawn
        if self.winners_drawn >= self.total_winners:
            self.current_draw.status = 'completed'
            self.current_draw.completed_at = datetime.utcnow()
            self.is_running = False
        
        db.session.commit()
        
        return {
            'phone_number': winner.phone_number,
            'position': self.winners_drawn,
            'total_winners': self.total_winners,
            'draw_complete': self.winners_drawn >= self.total_winners
        }
    
    def get_animation_sequence(self, duration=5):
        """Generate animation sequence for the draw display"""
        if not self.is_running:
            return []
        
        participants = [p for p in self.participants 
                       if not any(w.participant_id == p.id for w in self.current_draw.winners)]
        
        sequence = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            if participants:
                random_phone = random.choice(participants).phone_number
                sequence.append({
                    'phone_number': random_phone,
                    'timestamp': time.time()
                })
            time.sleep(0.1)  # Fast animation
        
        return sequence

# Global draw engine instance
draw_engine = DrawEngine()