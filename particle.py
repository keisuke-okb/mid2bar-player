import pygame
import random

from tools import draw_sparkle


class Particle:
    """汎用キラキラパーティクル"""

    def __init__(self, x, y, size_range=(2, 4), life_decay=0.02, colors=None, v=1):
        self.x = x
        self.y = y
        self.vx = random.uniform(-v, v)
        self.vy = random.uniform(-v, v)
        self.life = 1.0
        self.size = random.randint(*size_range)
        self.life_decay = life_decay
        if colors is None:
            self.color = random.choice(
                [
                    (255, 179, 186),
                    (255, 223, 186),
                    (255, 255, 186),
                    (186, 255, 201),
                    (186, 225, 255),
                    (219, 186, 255),
                    (255, 186, 245),
                    (255, 214, 255),
                    (214, 255, 255),
                    (255, 240, 200),
                ]
            )
        else:
            self.color = random.choice(colors)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.life_decay
        # self.vy に重力などを入れる場合はここで調整（現在は 0）

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(max(0, min(1, self.life)) * 255)
        color_with_alpha = (*self.color, alpha)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        draw_sparkle(s, color_with_alpha, (self.size, self.size), self.size)
        surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))


class MicInputParticle(Particle):
    """マイク入力風パーティクル（派生）"""

    def __init__(self, x, y):
        super().__init__(
            x, y, size_range=(5, 10), life_decay=0.05, colors=[(255, 255, 0)]
        )
        # 追加の初期化が必要ならここに記述
