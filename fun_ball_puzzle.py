import pygame
import sys
import random
import os
import json
from pygame import mixer

# Initialize pygame
pygame.init()
mixer.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)

# Create game window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Advanced Fun Ball Puzzle")
clock = pygame.time.Clock()

# Load assets
def load_assets():
    assets = {}
    
    # Create assets directory if it doesn't exist
    if not os.path.exists('assets'):
        os.makedirs('assets')
    if not os.path.exists('assets/sounds'):
        os.makedirs('assets/sounds')
    if not os.path.exists('assets/images'):
        os.makedirs('assets/images')
    
    # Load fonts
    assets['font_large'] = pygame.font.SysFont('Arial', 48)
    assets['font_medium'] = pygame.font.SysFont('Arial', 36)
    assets['font_small'] = pygame.font.SysFont('Arial', 24)
    
    # Create and save placeholder background if it doesn't exist
    bg_path = 'assets/images/background.png'
    if not os.path.exists(bg_path):
        bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        # Create a gradient background
        for y in range(SCREEN_HEIGHT):
            color = (0, 0, max(0, min(255, int(y / SCREEN_HEIGHT * 255))))
            pygame.draw.line(bg_surface, color, (0, y), (SCREEN_WIDTH, y))
        # Add some stars
        for _ in range(100):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            radius = random.randint(1, 3)
            pygame.draw.circle(bg_surface, WHITE, (x, y), radius)
        pygame.image.save(bg_surface, bg_path)
    
    assets['background'] = pygame.image.load(bg_path)
    
    # Create placeholder sounds
    sound_files = {
        'catch': 'assets/sounds/catch.wav',
        'powerup': 'assets/sounds/powerup.wav',
        'miss': 'assets/sounds/miss.wav',
        'game_over': 'assets/sounds/game_over.wav'
    }
    
    assets['sounds'] = {}
    for sound_name, sound_path in sound_files.items():
        if not os.path.exists(sound_path):
            # Create a silent sound file as placeholder
            dummy_sound = pygame.mixer.Sound(buffer=bytearray([0] * 44100))
            assets['sounds'][sound_name] = dummy_sound
        else:
            assets['sounds'][sound_name] = pygame.mixer.Sound(sound_path)
    
    return assets

# Ball class
class Ball:
    def __init__(self, x, y, radius, color, speed_x, speed_y, is_powerup=False, powerup_type=None):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.is_powerup = is_powerup
        self.powerup_type = powerup_type
        self.active = True
    
    def update(self, time_factor=1.0):
        # Update position
        self.x += self.speed_x * time_factor
        self.y += self.speed_y * time_factor
        
        # Bounce off walls
        if self.x <= self.radius or self.x >= SCREEN_WIDTH - self.radius:
            self.speed_x = -self.speed_x
            self.x = max(self.radius, min(self.x, SCREEN_WIDTH - self.radius))
        
        # Ball goes out of bottom screen
        if self.y > SCREEN_HEIGHT + self.radius:
            self.active = False
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        
        # Draw special effect for powerup balls
        if self.is_powerup:
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius - 3, 2)
            
            # Draw symbol based on powerup type
            if self.powerup_type == "bonus":
                text = assets['font_small'].render("+", True, WHITE)
                screen.blit(text, (self.x - text.get_width() // 2, self.y - text.get_height() // 2))
            elif self.powerup_type == "slow":
                text = assets['font_small'].render("S", True, WHITE)
                screen.blit(text, (self.x - text.get_width() // 2, self.y - text.get_height() // 2))
            elif self.powerup_type == "wide":
                text = assets['font_small'].render("W", True, WHITE)
                screen.blit(text, (self.x - text.get_width() // 2, self.y - text.get_height() // 2))

# Paddle class
class Paddle:
    def __init__(self, width, height, color):
        self.width = width
        self.height = height
        self.color = color
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - 30
        self.speed = 10
        self.original_width = width
        self.wide_effect_timer = 0
    
    def update(self, keys):
        if keys[pygame.K_LEFT]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.x += self.speed
        
        # Keep paddle within screen bounds
        self.x = max(self.width // 2, min(self.x, SCREEN_WIDTH - self.width // 2))
        
        # Update wide effect timer
        if self.wide_effect_timer > 0:
            self.wide_effect_timer -= 1
            if self.wide_effect_timer == 0:
                self.width = self.original_width
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, 
                        (self.x - self.width // 2, self.y - self.height // 2, 
                         self.width, self.height))
        
        # Draw effect when paddle is widened
        if self.wide_effect_timer > 0:
            pygame.draw.rect(screen, WHITE, 
                            (self.x - self.width // 2, self.y - self.height // 2, 
                             self.width, self.height), 2)
    
    def apply_wide_effect(self, duration):
        self.width = self.original_width * 2
        self.wide_effect_timer = duration

# Game class
class Game:
    def __init__(self, assets):
        self.assets = assets
        self.reset()
        self.load_high_score()
        self.state = "start"  # start, playing, paused, game_over
    
    def reset(self):
        self.paddle = Paddle(100, 15, WHITE)
        self.balls = []
        self.score = 0
        self.time_left = 60 * FPS  # 60 seconds in frames
        self.time_factor = 1.0
        self.slow_effect_timer = 0
        self.streak = 0
        self.max_streak = 0
        self.spawn_timer = 0
        self.spawn_interval = 60  # Spawn a new ball every 60 frames (1 second)
    
    def load_high_score(self):
        try:
            if os.path.exists('highscore.json'):
                with open('highscore.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('high_score', 0)
            else:
                self.high_score = 0
        except:
            self.high_score = 0
    
    def save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
            with open('highscore.json', 'w') as f:
                json.dump({'high_score': self.high_score}, f)
    
    def spawn_ball(self, powerup=False):
        radius = random.randint(10, 20)
        x = random.randint(radius, SCREEN_WIDTH - radius)
        y = -radius
        
        colors = [RED, GREEN, BLUE, YELLOW, PURPLE, CYAN, ORANGE]
        color = random.choice(colors)
        
        speed_x = random.uniform(-3, 3)
        speed_y = random.uniform(2, 5)
        
        powerup_type = None
        if powerup:
            powerup_type = random.choice(["bonus", "slow", "wide"])
            
        self.balls.append(Ball(x, y, radius, color, speed_x, speed_y, powerup, powerup_type))
    
    def update(self):
        if self.state != "playing":
            return
        
        # Update timer
        self.time_left -= 1
        if self.time_left <= 0:
            self.state = "game_over"
            self.save_high_score()
            self.assets['sounds']['game_over'].play()
            return
        
        # Update slow effect timer
        if self.slow_effect_timer > 0:
            self.slow_effect_timer -= 1
            self.time_factor = 0.5
            if self.slow_effect_timer == 0:
                self.time_factor = 1.0
        
        # Update paddle
        keys = pygame.key.get_pressed()
        self.paddle.update(keys)
        
        # Update balls
        for ball in self.balls[:]:
            ball.update(self.time_factor)
            
            # Check for collision with paddle
            if (ball.y + ball.radius >= self.paddle.y - self.paddle.height // 2 and
                ball.y - ball.radius <= self.paddle.y + self.paddle.height // 2 and
                ball.x + ball.radius >= self.paddle.x - self.paddle.width // 2 and
                ball.x - ball.radius <= self.paddle.x + self.paddle.width // 2):
                
                # Ball caught
                self.balls.remove(ball)
                
                # Handle powerups
                if ball.is_powerup:
                    self.assets['sounds']['powerup'].play()
                    if ball.powerup_type == "bonus":
                        self.score += 50
                    elif ball.powerup_type == "slow":
                        self.slow_effect_timer = 5 * FPS  # 5 seconds
                        self.time_factor = 0.5
                    elif ball.powerup_type == "wide":
                        self.paddle.apply_wide_effect(5 * FPS)  # 5 seconds
                else:
                    self.assets['sounds']['catch'].play()
                    self.score += 10
                
                # Update streak
                self.streak += 1
                if self.streak > self.max_streak:
                    self.max_streak = self.streak
                
                # Bonus points for streak
                if self.streak >= 3:
                    streak_bonus = (self.streak - 2) * 5  # 5 points per streak level above 2
                    self.score += streak_bonus
            
            # Remove balls that are no longer active
            elif not ball.active:
                self.balls.remove(ball)
                self.streak = 0  # Reset streak when a ball is missed
                self.assets['sounds']['miss'].play()
        
        # Spawn new balls
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            
            # 20% chance to spawn a powerup ball
            if random.random() < 0.2:
                self.spawn_ball(powerup=True)
            else:
                self.spawn_ball()
    
    def draw(self, screen):
        # Draw background
        screen.blit(self.assets['background'], (0, 0))
        
        if self.state == "start":
            self.draw_start_screen(screen)
        elif self.state == "playing" or self.state == "paused":
            # Draw game elements
            self.paddle.draw(screen)
            for ball in self.balls:
                ball.draw(screen)
            
            # Draw UI
            self.draw_ui(screen)
            
            if self.state == "paused":
                self.draw_pause_screen(screen)
        elif self.state == "game_over":
            self.draw_game_over_screen(screen)
    
    def draw_ui(self, screen):
        # Draw score
        score_text = self.assets['font_medium'].render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (20, 20))
        
        # Draw time left
        time_left_seconds = self.time_left // FPS
        time_text = self.assets['font_medium'].render(f"Time: {time_left_seconds}", True, WHITE)
        screen.blit(time_text, (SCREEN_WIDTH - time_text.get_width() - 20, 20))
        
        # Draw streak
        if self.streak >= 3:
            streak_text = self.assets['font_small'].render(f"Streak: {self.streak}x", True, YELLOW)
            screen.blit(streak_text, (SCREEN_WIDTH // 2 - streak_text.get_width() // 2, 20))
        
        # Draw effect indicators
        y_pos = 60
        if self.slow_effect_timer > 0:
            slow_text = self.assets['font_small'].render("SLOW TIME", True, CYAN)
            screen.blit(slow_text, (20, y_pos))
            y_pos += 30
        
        if self.paddle.wide_effect_timer > 0:
            wide_text = self.assets['font_small'].render("WIDE PADDLE", True, GREEN)
            screen.blit(wide_text, (20, y_pos))
    
    def draw_start_screen(self, screen):
        title_text = self.assets['font_large'].render("Fun Ball Puzzle", True, WHITE)
        screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 100))
        
        instructions = [
            "Catch falling balls with your paddle to score points",
            "Use LEFT and RIGHT arrow keys to move",
            "Special power-up balls give bonus effects:",
            "  + : Bonus points",
            "  S : Slow down time",
            "  W : Widen paddle",
            "Catch multiple balls in a row for streak bonus!",
            "Press P to pause/resume the game",
            "",
            "Press SPACE to start"
        ]
        
        y_pos = 200
        for line in instructions:
            instr_text = self.assets['font_small'].render(line, True, WHITE)
            screen.blit(instr_text, (SCREEN_WIDTH // 2 - instr_text.get_width() // 2, y_pos))
            y_pos += 30
    
    def draw_pause_screen(self, screen):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))
        
        pause_text = self.assets['font_large'].render("PAUSED", True, WHITE)
        screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        
        continue_text = self.assets['font_medium'].render("Press P to continue", True, WHITE)
        screen.blit(continue_text, (SCREEN_WIDTH // 2 - continue_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))
    
    def draw_game_over_screen(self, screen):
        game_over_text = self.assets['font_large'].render("GAME OVER", True, RED)
        screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, 150))
        
        score_text = self.assets['font_medium'].render(f"Your Score: {self.score}", True, WHITE)
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 250))
        
        high_score_text = self.assets['font_medium'].render(f"High Score: {self.high_score}", True, YELLOW)
        screen.blit(high_score_text, (SCREEN_WIDTH // 2 - high_score_text.get_width() // 2, 300))
        
        if self.max_streak > 2:
            streak_text = self.assets['font_small'].render(f"Max Streak: {self.max_streak}x", True, GREEN)
            screen.blit(streak_text, (SCREEN_WIDTH // 2 - streak_text.get_width() // 2, 350))
        
        restart_text = self.assets['font_medium'].render("Press SPACE to play again", True, WHITE)
        screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 400))
        
        quit_text = self.assets['font_small'].render("Press ESC to quit", True, WHITE)
        screen.blit(quit_text, (SCREEN_WIDTH // 2 - quit_text.get_width() // 2, 450))

# Main function
def main():
    global assets
    
    # Load assets
    assets = load_assets()
    
    # Create game instance
    game = Game(assets)
    
    # Main game loop
    running = True
    while running:
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                if event.key == pygame.K_p:
                    if game.state == "playing":
                        game.state = "paused"
                    elif game.state == "paused":
                        game.state = "playing"
                
                if event.key == pygame.K_SPACE:
                    if game.state == "start" or game.state == "game_over":
                        game.reset()
                        game.state = "playing"
        
        # Update game state
        game.update()
        
        # Draw everything
        game.draw(screen)
        
        # Update display
        pygame.display.flip()
        
        # Cap the frame rate
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
