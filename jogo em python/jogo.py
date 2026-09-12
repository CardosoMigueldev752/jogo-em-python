"""
BOSS RUSH - 5 Chefes, 5 estilos de luta
=========================================
Jogo de ação top-down feito com pygame, focado 100% em lutas contra chefes.

Os 5 chefes (cada um com um jeito de lutar bem diferente):
    1. Guardião de Pedra  - bruto corpo a corpo: investidas e ondas de impacto
    2. Bruxa das Trevas   - teleporte, orbes perseguidoras e raio giratório
    3. Serpente de Cristal- orbita a arena disparando espirais de cristais
    4. Golem de Fogo      - deixa poças de fogo no chão e chama meteoros
    5. Rei Demônio        - chefe final, combina investidas, leques, invocação
                            de servos e uma espiral na fase final

Como jogar:
    - Mover: W A S D ou setas do teclado
    - Mirar: mouse
    - Atirar: botão esquerdo do mouse (segure para atirar continuamente)
    - Dash (dodge): ESPAÇO ou SHIFT - te torna invulnerável por um instante
    - A vida é restaurada por completo entre um chefe e outro
    - Se morrer, você tenta de novo apenas o chefe atual (tecla R)

Para rodar:
    pip install pygame
    python3 boss_rush.py
"""

import pygame
import random
import math
import sys

pygame.init()

# ----------------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ----------------------------------------------------------------------------
LARGURA, ALTURA = 1000, 710
HUD_ALTURA = 70
FPS = 60

# Cores
PRETO = (10, 10, 15)
BRANCO = (240, 240, 240)
CINZA = (70, 70, 80)
CINZA_CLARO = (150, 150, 160)
VERMELHO = (205, 45, 45)
VERMELHO_ESCURO = (120, 20, 20)
VERDE = (45, 200, 90)
CIANO = (80, 220, 220)
AMARELO = (235, 205, 45)
LARANJA = (230, 130, 40)
ROXO = (155, 65, 205)
DOURADO = (212, 175, 55)
MARROM = (120, 78, 45)
FUNDO = (24, 22, 30)
FUNDO_GRADE = (34, 32, 40)


# ----------------------------------------------------------------------------
# FUNÇÕES UTILITÁRIAS
# ----------------------------------------------------------------------------
def circulo_colide_retangulo(cx, cy, raio, retangulo):
    mais_perto_x = max(retangulo.left, min(cx, retangulo.right))
    mais_perto_y = max(retangulo.top, min(cy, retangulo.bottom))
    dist_x = cx - mais_perto_x
    dist_y = cy - mais_perto_y
    return (dist_x * dist_x + dist_y * dist_y) < (raio * raio)


def mover_com_colisao(x, y, dx, dy, raio, paredes):
    novo_x = x + dx
    if not any(circulo_colide_retangulo(novo_x, y, raio, p) for p in paredes):
        x = novo_x
    novo_y = y + dy
    if not any(circulo_colide_retangulo(x, novo_y, raio, p) for p in paredes):
        y = novo_y
    return x, y


def distancia_ponto_segmento(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    comprimento2 = dx * dx + dy * dy
    if comprimento2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / comprimento2))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def criar_paredes_borda():
    espessura = 24
    return [
        pygame.Rect(0, HUD_ALTURA, LARGURA, espessura),
        pygame.Rect(0, ALTURA - espessura, LARGURA, espessura),
        pygame.Rect(0, HUD_ALTURA, espessura, ALTURA - HUD_ALTURA),
        pygame.Rect(LARGURA - espessura, HUD_ALTURA, espessura, ALTURA - HUD_ALTURA),
    ]


def obstaculos_arena():
    margem = 90
    return [
        pygame.Rect(120, HUD_ALTURA + margem, 30, 30),
        pygame.Rect(LARGURA - 150, HUD_ALTURA + margem, 30, 30),
        pygame.Rect(120, ALTURA - margem - 30, 30, 30),
        pygame.Rect(LARGURA - 150, ALTURA - margem - 30, 30, 30),
    ]


# ----------------------------------------------------------------------------
# PROJÉTEIS
# ----------------------------------------------------------------------------
class Projetil:
    def __init__(self, x, y, alvo_dx, alvo_dy, dono, dano, cor, raio=5, velocidade=9, homing=0.0, alvo=None):
        self.x = x
        self.y = y
        angulo = math.atan2(alvo_dy, alvo_dx)
        self.vx = math.cos(angulo) * velocidade
        self.vy = math.sin(angulo) * velocidade
        self.dono = dono  # 'jogador' ou 'inimigo'
        self.dano = dano
        self.cor = cor
        self.raio = raio
        self.homing = homing
        self.alvo = alvo
        self.velocidade_escalar = velocidade
        self.vivo = True

    def atualizar(self):
        if self.homing > 0 and self.alvo is not None:
            dx = self.alvo.x - self.x
            dy = self.alvo.y - self.y
            dist = math.hypot(dx, dy) or 1
            dxn, dyn = dx / dist, dy / dist
            vx_alvo = dxn * self.velocidade_escalar
            vy_alvo = dyn * self.velocidade_escalar
            self.vx += (vx_alvo - self.vx) * self.homing
            self.vy += (vy_alvo - self.vy) * self.homing
        self.x += self.vx
        self.y += self.vy
        if self.x < -50 or self.x > LARGURA + 50 or self.y < HUD_ALTURA - 50 or self.y > ALTURA + 50:
            self.vivo = False

    def desenhar(self, tela):
        pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)
        pygame.draw.circle(tela, BRANCO, (int(self.x), int(self.y)), self.raio, 1)


# ----------------------------------------------------------------------------
# ÁREAS DE PERIGO (avisos no chão, poças de fogo, impactos de meteoro)
# ----------------------------------------------------------------------------
class Perigo:
    def __init__(self, x, y, raio, aviso=0.0, ativo=1.0, dano=10, cor=VERMELHO,
                 dano_continuo=False, intervalo_tick=0.4):
        self.x = x
        self.y = y
        self.raio = raio
        self.timer_aviso = aviso
        self.timer_ativo = ativo
        self.dano = dano
        self.cor = cor
        self.dano_continuo = dano_continuo
        self.intervalo_tick = intervalo_tick
        self.timer_tick = 0.0
        self.atingiu = False
        self.vivo = True
        self.fase = "aviso" if aviso > 0 else "ativo"

    def atualizar(self, dt, jogador):
        if self.fase == "aviso":
            self.timer_aviso -= dt
            if self.timer_aviso <= 0:
                self.fase = "ativo"
        elif self.fase == "ativo":
            self.timer_ativo -= dt
            dist = math.hypot(jogador.x - self.x, jogador.y - self.y)
            dentro = dist < self.raio + jogador.raio
            if self.dano_continuo:
                self.timer_tick -= dt
                if dentro and self.timer_tick <= 0:
                    jogador.receber_dano(self.dano)
                    self.timer_tick = self.intervalo_tick
            else:
                if dentro and not self.atingiu:
                    jogador.receber_dano(self.dano)
                    self.atingiu = True
            if self.timer_ativo <= 0:
                self.vivo = False

    def desenhar(self, tela):
        if self.fase == "aviso":
            s = pygame.Surface((self.raio * 2, self.raio * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 60, 40, 90), (self.raio, self.raio), self.raio)
            pygame.draw.circle(s, (255, 90, 60, 210), (self.raio, self.raio), self.raio, 3)
            tela.blit(s, (self.x - self.raio, self.y - self.raio))
        else:
            s = pygame.Surface((self.raio * 2, self.raio * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.cor, 130), (self.raio, self.raio), self.raio)
            tela.blit(s, (self.x - self.raio, self.y - self.raio))


# ----------------------------------------------------------------------------
# RAIO GIRATÓRIO (usado pela Bruxa das Trevas)
# ----------------------------------------------------------------------------
class Raio:
    def __init__(self, x, y, angulo_inicial, velocidade_angular, comprimento, duracao, dano, largura=16):
        self.x = x
        self.y = y
        self.angulo = angulo_inicial
        self.vel_angular = velocidade_angular
        self.comprimento = comprimento
        self.duracao = duracao
        self.dano = dano
        self.largura = largura
        self.timer_tick = 0.0
        self.vivo = True

    def atualizar(self, dt, jogador):
        self.angulo += self.vel_angular * dt
        self.duracao -= dt
        if self.duracao <= 0:
            self.vivo = False
            return
        fx = self.x + math.cos(self.angulo) * self.comprimento
        fy = self.y + math.sin(self.angulo) * self.comprimento
        d = distancia_ponto_segmento(jogador.x, jogador.y, self.x, self.y, fx, fy)
        self.timer_tick -= dt
        if d < self.largura / 2 + jogador.raio and self.timer_tick <= 0:
            jogador.receber_dano(self.dano)
            self.timer_tick = 0.3

    def desenhar(self, tela):
        fx = self.x + math.cos(self.angulo) * self.comprimento
        fy = self.y + math.sin(self.angulo) * self.comprimento
        s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.line(s, (210, 70, 230, 160), (self.x, self.y), (fx, fy), self.largura)
        tela.blit(s, (0, 0))
        pygame.draw.line(tela, BRANCO, (self.x, self.y), (fx, fy), 2)


# ----------------------------------------------------------------------------
# JOGADOR
# ----------------------------------------------------------------------------
class Jogador:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.raio = 14
        self.velocidade = 4.3
        self.vida_max = 120
        self.vida = 120
        self.cor = CIANO
        self.dano_tiro = 11
        self.cooldown_tiro = 0.22
        self.tempo_desde_tiro = 999.0
        self.invulneravel_timer = 0.0

        self.dash_cooldown = 1.1
        self.dash_duracao = 0.16
        self.dash_velocidade = 11.0
        self.dash_timer = 0.0
        self.tempo_desde_dash = 999.0
        self.dash_dx, self.dash_dy = 0.0, -1.0
        self._ultima_direcao = (0.0, -1.0)

    def mover(self, teclas, paredes, dt):
        dx = dy = 0
        if teclas[pygame.K_w] or teclas[pygame.K_UP]:
            dy -= 1
        if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:
            dy += 1
        if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
            dx -= 1
        if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
            dx += 1
        if dx != 0 or dy != 0:
            norm = math.hypot(dx, dy)
            dx, dy = dx / norm, dy / norm
            self._ultima_direcao = (dx, dy)

        if self.dash_timer > 0:
            vx = self.dash_dx * self.dash_velocidade
            vy = self.dash_dy * self.dash_velocidade
            self.dash_timer -= dt
        else:
            vx, vy = dx * self.velocidade, dy * self.velocidade

        self.x, self.y = mover_com_colisao(self.x, self.y, vx, vy, self.raio, paredes)
        self.x = max(self.raio, min(LARGURA - self.raio, self.x))
        self.y = max(HUD_ALTURA + self.raio, min(ALTURA - self.raio, self.y))
        self.tempo_desde_dash += dt

    def tentar_dash(self):
        if self.dash_timer <= 0 and self.tempo_desde_dash >= self.dash_cooldown:
            dx, dy = self._ultima_direcao
            if dx == 0 and dy == 0:
                dx, dy = 0, -1
            self.dash_dx, self.dash_dy = dx, dy
            self.dash_timer = self.dash_duracao
            self.tempo_desde_dash = 0.0
            self.invulneravel_timer = max(self.invulneravel_timer, self.dash_duracao + 0.15)

    def atualizar_timers(self, dt):
        self.tempo_desde_tiro += dt
        if self.invulneravel_timer > 0:
            self.invulneravel_timer -= dt

    def atirar(self, alvo_x, alvo_y, lista_projeteis):
        if self.tempo_desde_tiro >= self.cooldown_tiro:
            self.tempo_desde_tiro = 0
            lista_projeteis.append(
                Projetil(self.x, self.y, alvo_x - self.x, alvo_y - self.y,
                          "jogador", self.dano_tiro, AMARELO, raio=5, velocidade=12)
            )

    def receber_dano(self, dano):
        if self.invulneravel_timer <= 0:
            self.vida -= dano
            self.invulneravel_timer = 0.5
            return True
        return False

    def desenhar(self, tela):
        cor = self.cor
        if self.dash_timer > 0:
            cor = BRANCO
        elif self.invulneravel_timer > 0 and int(self.invulneravel_timer * 20) % 2 == 0:
            cor = BRANCO
        pygame.draw.circle(tela, cor, (int(self.x), int(self.y)), self.raio)
        pygame.draw.circle(tela, PRETO, (int(self.x), int(self.y)), self.raio, 2)
        mx, my = pygame.mouse.get_pos()
        ang = math.atan2(my - self.y, mx - self.x)
        ponta = (self.x + math.cos(ang) * (self.raio + 8), self.y + math.sin(ang) * (self.raio + 8))
        pygame.draw.line(tela, BRANCO, (self.x, self.y), ponta, 2)


# ----------------------------------------------------------------------------
# SERVO (minion invocado pelo Rei Demônio)
# ----------------------------------------------------------------------------
class Servo:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vida = 16
        self.velocidade = 2.6
        self.dano = 8
        self.raio = 10
        self.cor = VERMELHO
        self.vivo = True
        self.timer_contato = 0.0
        self.cooldown_contato = 0.8

    def atualizar(self, jogador, paredes, dt):
        dx = jogador.x - self.x
        dy = jogador.y - self.y
        dist = math.hypot(dx, dy) or 1
        dxn, dyn = dx / dist, dy / dist
        self.x, self.y = mover_com_colisao(self.x, self.y, dxn * self.velocidade, dyn * self.velocidade, self.raio, paredes)
        self.timer_contato -= dt
        if dist < self.raio + jogador.raio + 4 and self.timer_contato <= 0:
            if jogador.receber_dano(self.dano):
                self.timer_contato = self.cooldown_contato

    def receber_dano(self, dano):
        self.vida -= dano
        if self.vida <= 0:
            self.vivo = False

    def desenhar(self, tela):
        pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)
        pygame.draw.circle(tela, PRETO, (int(self.x), int(self.y)), self.raio, 2)


# ----------------------------------------------------------------------------
# CLASSE BASE DOS CHEFES
# ----------------------------------------------------------------------------
class ChefeBase:
    nome = "Chefe"

    def __init__(self, x, y, vida, cor, raio):
        self.x = x
        self.y = y
        self.vida_max = vida
        self.vida = vida
        self.cor = cor
        self.raio = raio
        self.vivo = True
        self.fase2 = False
        self.fase3 = False
        self.usa_fase3 = False
        self.dano_contato = 14
        self.cooldown_contato = 0.7
        self.timer_contato = 0.0

    def checar_fases(self):
        if not self.fase2 and self.vida <= self.vida_max * 0.5:
            self.fase2 = True
            self.ao_entrar_fase2()
        if self.usa_fase3 and not self.fase3 and self.vida <= self.vida_max / 3:
            self.fase3 = True
            self.ao_entrar_fase3()

    def ao_entrar_fase2(self):
        pass

    def ao_entrar_fase3(self):
        pass

    def dano_de_contato(self, jogador, dt):
        dist = math.hypot(jogador.x - self.x, jogador.y - self.y)
        self.timer_contato -= dt
        if dist < self.raio + jogador.raio + 4 and self.timer_contato <= 0:
            if jogador.receber_dano(self.dano_contato):
                self.timer_contato = self.cooldown_contato

    def receber_dano(self, dano):
        self.vida -= dano
        if self.vida <= 0:
            self.vida = 0
            self.vivo = False

    def desenhar(self, tela):
        pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)
        pygame.draw.circle(tela, PRETO, (int(self.x), int(self.y)), self.raio, 3)


# ----------------------------------------------------------------------------
# CHEFE 1 - GUARDIÃO DE PEDRA (bruto corpo a corpo)
# ----------------------------------------------------------------------------
class GuardiaoDePedra(ChefeBase):
    nome = "Guardião de Pedra"

    def __init__(self, x, y):
        super().__init__(x, y, vida=240, cor=MARROM, raio=38)
        self.velocidade = 1.7
        self.dano_contato = 16
        self.timer_acao = 2.0
        self.estado = "perseguir"  # perseguir, telegraph_investida, investindo, telegraph_impacto
        self.timer_estado = 0.0
        self.dir_investida = (0.0, 0.0)

    def ao_entrar_fase2(self):
        self.velocidade *= 1.2

    def atualizar(self, jogador, paredes, dt, projeteis, perigos, raios, minions):
        self.checar_fases()
        dx = jogador.x - self.x
        dy = jogador.y - self.y
        dist = math.hypot(dx, dy) or 1
        dxn, dyn = dx / dist, dy / dist

        if self.estado == "perseguir":
            self.x, self.y = mover_com_colisao(self.x, self.y, dxn * self.velocidade, dyn * self.velocidade, self.raio, paredes)
            self.dano_de_contato(jogador, dt)
            self.timer_acao -= dt
            if self.timer_acao <= 0:
                if random.random() < 0.5:
                    self.estado = "telegraph_investida"
                    self.timer_estado = 0.6
                else:
                    self.estado = "telegraph_impacto"
                    self.timer_estado = 0.55

        elif self.estado == "telegraph_investida":
            self.timer_estado -= dt
            if self.timer_estado <= 0:
                dx2 = jogador.x - self.x
                dy2 = jogador.y - self.y
                d2 = math.hypot(dx2, dy2) or 1
                self.dir_investida = (dx2 / d2, dy2 / d2)
                self.estado = "investindo"
                self.timer_estado = 0.5

        elif self.estado == "investindo":
            vdx, vdy = self.dir_investida
            self.x, self.y = mover_com_colisao(self.x, self.y, vdx * 9, vdy * 9, self.raio, paredes)
            self.dano_de_contato(jogador, dt)
            self.timer_estado -= dt
            if self.timer_estado <= 0:
                self.estado = "perseguir"
                self.timer_acao = 1.8 if self.fase2 else 2.6

        elif self.estado == "telegraph_impacto":
            self.timer_estado -= dt
            if self.timer_estado <= 0:
                self.estado = "perseguir"
                self.timer_acao = 2.0 if self.fase2 else 2.8
                n = 16 if self.fase2 else 12
                for i in range(n):
                    ang = 2 * math.pi * i / n
                    projeteis.append(Projetil(self.x, self.y, math.cos(ang), math.sin(ang), "inimigo", 12, MARROM, raio=7, velocidade=5.5))

    def desenhar(self, tela):
        cor = self.cor
        if self.estado in ("telegraph_investida", "telegraph_impacto"):
            pulso = int(40 * math.sin(pygame.time.get_ticks() / 40))
            cor = (min(255, self.cor[0] + 80 + pulso), self.cor[1], self.cor[2])
        elif self.estado == "investindo":
            cor = AMARELO
        pygame.draw.circle(tela, cor, (int(self.x), int(self.y)), self.raio)
        pygame.draw.circle(tela, PRETO, (int(self.x), int(self.y)), self.raio, 3)


# ----------------------------------------------------------------------------
# CHEFE 2 - BRUXA DAS TREVAS (teleporte + à distância)
# ----------------------------------------------------------------------------
class BruxaDasTrevas(ChefeBase):
    nome = "Bruxa das Trevas"

    def __init__(self, x, y):
        super().__init__(x, y, vida=190, cor=ROXO, raio=22)
        self.dano_contato = 10
        self.timer_teleporte = 2.3
        self.timer_orbes = 1.6
        self.timer_raio = 3.6

    def teleportar(self, paredes):
        margem = 90
        for _ in range(20):
            nx = random.randint(margem, LARGURA - margem)
            ny = random.randint(HUD_ALTURA + margem, ALTURA - margem)
            if not any(circulo_colide_retangulo(nx, ny, self.raio, p) for p in paredes):
                self.x, self.y = nx, ny
                return

    def atualizar(self, jogador, paredes, dt, projeteis, perigos, raios, minions):
        self.checar_fases()
        self.dano_de_contato(jogador, dt)

        self.timer_teleporte -= dt
        if self.timer_teleporte <= 0:
            self.timer_teleporte = 1.6 if self.fase2 else 2.3
            self.teleportar(paredes)

        self.timer_orbes -= dt
        if self.timer_orbes <= 0:
            n = 5 if self.fase2 else 3
            self.timer_orbes = 1.9 if self.fase2 else 2.6
            for _ in range(n):
                ang = random.uniform(0, 2 * math.pi)
                projeteis.append(Projetil(self.x, self.y, math.cos(ang), math.sin(ang), "inimigo", 9, ROXO,
                                           raio=6, velocidade=3.4, homing=0.045, alvo=jogador))

        self.timer_raio -= dt
        if self.timer_raio <= 0:
            self.timer_raio = 5.5 if not self.fase2 else 3.8
            ang0 = math.atan2(jogador.y - self.y, jogador.x - self.x) - 0.8
            vel_ang = 1.6 if not self.fase2 else 2.4
            raios.append(Raio(self.x, self.y, ang0, vel_ang, comprimento=1000, duracao=1.6, dano=8, largura=16))
            if self.fase2:
                raios.append(Raio(self.x, self.y, ang0 + math.pi, -vel_ang, comprimento=1000, duracao=1.6, dano=8, largura=16))


# ----------------------------------------------------------------------------
# CHEFE 3 - SERPENTE DE CRISTAL (orbita a arena, espiral de projéteis)
# ----------------------------------------------------------------------------
class SerpenteDeCristal(ChefeBase):
    nome = "Serpente de Cristal"

    def __init__(self, x, y):
        super().__init__(x, y, vida=210, cor=CIANO, raio=26)
        self.dano_contato = 12
        self.tempo = 0.0
        self.raio_orbita = 220
        self.centro = (LARGURA / 2, HUD_ALTURA + (ALTURA - HUD_ALTURA) / 2)
        self.vel_angular = 0.9
        self.angulo = 0.0
        self.timer_espiral = 0.0
        self.angulo_espiral = 0.0
        self.timer_rajada = 3.0

    def ao_entrar_fase2(self):
        self.vel_angular *= 1.4

    def atualizar(self, jogador, paredes, dt, projeteis, perigos, raios, minions):
        self.checar_fases()
        self.angulo += self.vel_angular * dt
        self.tempo += dt
        cx, cy = self.centro
        raio_var = self.raio_orbita + 60 * math.sin(self.tempo * 0.6)
        self.x = cx + math.cos(self.angulo) * raio_var
        self.y = cy + math.sin(self.angulo) * raio_var
        self.dano_de_contato(jogador, dt)

        self.timer_espiral -= dt
        intervalo = 0.09 if self.fase2 else 0.14
        if self.timer_espiral <= 0:
            self.timer_espiral = intervalo
            bracos = 3 if self.fase2 else 2
            for b in range(bracos):
                ang = self.angulo_espiral + b * (2 * math.pi / bracos)
                projeteis.append(Projetil(self.x, self.y, math.cos(ang), math.sin(ang), "inimigo", 8, CIANO, raio=5, velocidade=4.2))
            self.angulo_espiral += 0.32

        self.timer_rajada -= dt
        if self.timer_rajada <= 0:
            self.timer_rajada = 3.0 if not self.fase2 else 2.1
            dx = jogador.x - self.x
            dy = jogador.y - self.y
            ang_base = math.atan2(dy, dx)
            n = 7
            abertura = math.pi / 2.2
            for i in range(n):
                a = ang_base - abertura / 2 + abertura * i / (n - 1)
                projeteis.append(Projetil(self.x, self.y, math.cos(a), math.sin(a), "inimigo", 11, BRANCO, raio=6, velocidade=6.5))


# ----------------------------------------------------------------------------
# CHEFE 4 - GOLEM DE FOGO (área de perigo: poças de fogo + meteoros)
# ----------------------------------------------------------------------------
class GolemDeFogo(ChefeBase):
    nome = "Golem de Fogo"

    def __init__(self, x, y):
        super().__init__(x, y, vida=280, cor=LARANJA, raio=34)
        self.velocidade = 1.3
        self.dano_contato = 15
        self.timer_meteoro = 2.6
        self.timer_poca = 1.0

    def ao_entrar_fase2(self):
        self.velocidade *= 1.15

    def atualizar(self, jogador, paredes, dt, projeteis, perigos, raios, minions):
        self.checar_fases()
        dx = jogador.x - self.x
        dy = jogador.y - self.y
        dist = math.hypot(dx, dy) or 1
        dxn, dyn = dx / dist, dy / dist
        self.x, self.y = mover_com_colisao(self.x, self.y, dxn * self.velocidade, dyn * self.velocidade, self.raio, paredes)
        self.dano_de_contato(jogador, dt)

        self.timer_poca -= dt
        if self.timer_poca <= 0:
            self.timer_poca = 1.1
            perigos.append(Perigo(self.x, self.y, 34, aviso=0.3, ativo=3.0, dano=6, cor=LARANJA,
                                   dano_continuo=True, intervalo_tick=0.5))

        self.timer_meteoro -= dt
        if self.timer_meteoro <= 0:
            self.timer_meteoro = 3.0 if not self.fase2 else 2.0
            n = 3 if not self.fase2 else 5
            for _ in range(n):
                ox = jogador.x + random.uniform(-90, 90)
                oy = jogador.y + random.uniform(-90, 90)
                ox = max(60, min(LARGURA - 60, ox))
                oy = max(HUD_ALTURA + 60, min(ALTURA - 60, oy))
                perigos.append(Perigo(ox, oy, 46, aviso=1.0, ativo=0.3, dano=18, cor=VERMELHO, dano_continuo=False))


# ----------------------------------------------------------------------------
# CHEFE 5 - REI DEMÔNIO (chefe final: combina vários padrões, 3 fases)
# ----------------------------------------------------------------------------
class ReiDemonio(ChefeBase):
    nome = "Rei Demônio"

    def __init__(self, x, y):
        super().__init__(x, y, vida=400, cor=VERMELHO_ESCURO, raio=40)
        self.velocidade = 1.9
        self.dano_contato = 18
        self.usa_fase3 = True
        self.timer_leque = 2.4
        self.timer_investida = 5.0
        self.timer_invocar = 6.5
        self.timer_espiral = 0.0
        self.angulo_espiral = 0.0
        self.estado = "perseguir"
        self.timer_estado = 0.0
        self.dir_investida = (0.0, 0.0)

    def ao_entrar_fase2(self):
        self.velocidade *= 1.15

    def ao_entrar_fase3(self):
        self.velocidade *= 1.15

    def atualizar(self, jogador, paredes, dt, projeteis, perigos, raios, minions):
        self.checar_fases()
        dx = jogador.x - self.x
        dy = jogador.y - self.y
        dist = math.hypot(dx, dy) or 1
        dxn, dyn = dx / dist, dy / dist

        if self.estado == "perseguir":
            self.x, self.y = mover_com_colisao(self.x, self.y, dxn * self.velocidade, dyn * self.velocidade, self.raio, paredes)
            self.dano_de_contato(jogador, dt)

            self.timer_investida -= dt
            if self.timer_investida <= 0:
                self.timer_investida = 3.0 if self.fase2 else 4.2
                self.estado = "telegraph"
                self.timer_estado = 0.5

            if self.fase2:
                self.timer_invocar -= dt
                if self.timer_invocar <= 0:
                    self.timer_invocar = 5.0 if self.fase3 else 7.0
                    for _ in range(2):
                        ox = self.x + random.uniform(-70, 70)
                        oy = self.y + random.uniform(-70, 70)
                        minions.append(Servo(ox, oy))

        elif self.estado == "telegraph":
            self.timer_estado -= dt
            if self.timer_estado <= 0:
                dx2 = jogador.x - self.x
                dy2 = jogador.y - self.y
                d2 = math.hypot(dx2, dy2) or 1
                self.dir_investida = (dx2 / d2, dy2 / d2)
                self.estado = "investindo"
                self.timer_estado = 0.4

        elif self.estado == "investindo":
            vdx, vdy = self.dir_investida
            self.x, self.y = mover_com_colisao(self.x, self.y, vdx * 10, vdy * 10, self.raio, paredes)
            self.dano_de_contato(jogador, dt)
            self.timer_estado -= dt
            if self.timer_estado <= 0:
                self.estado = "perseguir"

        limite = 2.4
        if self.fase2:
            limite = 1.6
        if self.fase3:
            limite = 1.0
        self.timer_leque -= dt
        if self.timer_leque <= 0:
            self.timer_leque = limite
            n = 6
            if self.fase2:
                n = 9
            if self.fase3:
                n = 12
            ang_base = math.atan2(dy, dx)
            abertura = math.pi / 2.6
            for i in range(n):
                a = ang_base - abertura / 2 + (abertura * i / (n - 1) if n > 1 else 0)
                projeteis.append(Projetil(self.x, self.y, math.cos(a), math.sin(a), "inimigo", 12, VERMELHO, raio=6, velocidade=6.0))

        if self.fase3:
            self.timer_espiral -= dt
            if self.timer_espiral <= 0:
                self.timer_espiral = 0.12
                for b in range(2):
                    ang = self.angulo_espiral + b * math.pi
                    projeteis.append(Projetil(self.x, self.y, math.cos(ang), math.sin(ang), "inimigo", 10, ROXO, raio=5, velocidade=5.0))
                self.angulo_espiral += 0.4

    def desenhar(self, tela):
        cor = self.cor
        if self.estado == "telegraph":
            pulso = int(40 * math.sin(pygame.time.get_ticks() / 40))
            cor = (min(255, cor[0] + 80 + pulso), cor[1], cor[2])
        elif self.estado == "investindo":
            cor = AMARELO
        pygame.draw.circle(tela, cor, (int(self.x), int(self.y)), self.raio)
        pygame.draw.circle(tela, PRETO, (int(self.x), int(self.y)), self.raio, 3)
        pygame.draw.circle(tela, DOURADO, (int(self.x), int(self.y)), self.raio - 12, 2)
        if self.fase3:
            pygame.draw.circle(tela, ROXO, (int(self.x), int(self.y)), self.raio - 20, 2)


LISTA_CHEFES = [GuardiaoDePedra, BruxaDasTrevas, SerpenteDeCristal, GolemDeFogo, ReiDemonio]


# ----------------------------------------------------------------------------
# CLASSE PRINCIPAL DO JOGO
# ----------------------------------------------------------------------------
class Jogo:
    def __init__(self):
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Boss Rush - 5 Chefes")
        self.relogio = pygame.time.Clock()
        self.fonte_grande = pygame.font.SysFont("arial", 44, bold=True)
        self.fonte_media = pygame.font.SysFont("arial", 26, bold=True)
        self.fonte_pequena = pygame.font.SysFont("arial", 18)

        self.estado = "MENU"
        self.jogador = None
        self.carregar_chefe(0)
        self.estado = "MENU"

    def iniciar_run(self):
        self.pontuacao = 0
        self.jogador = None
        self.carregar_chefe(0)

    def carregar_chefe(self, indice):
        self.indice_chefe = indice
        self.paredes = criar_paredes_borda() + obstaculos_arena()
        cls = LISTA_CHEFES[indice]
        self.chefe = cls(LARGURA / 2, HUD_ALTURA + 140)
        self.projeteis = []
        self.perigos = []
        self.raios = []
        self.minions = []

        px, py = LARGURA / 2, ALTURA - 80
        if self.jogador is None:
            self.jogador = Jogador(px, py)
            self.pontuacao = getattr(self, "pontuacao", 0)
        else:
            self.jogador.x, self.jogador.y = px, py
            self.jogador.vida = self.jogador.vida_max
            self.jogador.invulneravel_timer = 1.2
            self.jogador.dash_timer = 0.0
            self.jogador.tempo_desde_dash = 999.0

        self.mensagem = f"CHEFE {indice + 1}/5 - {self.chefe.nome}"
        self.mensagem_timer = 2.4

    # ------------------------------------------------------------------
    def tratar_evento(self, ev):
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if ev.type == pygame.KEYDOWN:
            if self.estado == "MENU" and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.iniciar_run()
                self.estado = "LUTANDO"
            elif self.estado == "LUTANDO" and ev.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.jogador.tentar_dash()
            elif self.estado == "GAME_OVER" and ev.key == pygame.K_r:
                self.carregar_chefe(self.indice_chefe)
                self.estado = "LUTANDO"
            elif self.estado == "VITORIA" and ev.key == pygame.K_r:
                self.iniciar_run()
                self.estado = "LUTANDO"
            elif ev.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    # ------------------------------------------------------------------
    def atualizar(self, dt):
        if self.estado == "LUTANDO":
            teclas = pygame.key.get_pressed()
            self.jogador.mover(teclas, self.paredes, dt)
            self.jogador.atualizar_timers(dt)

            mx, my = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                self.jogador.atirar(mx, my, self.projeteis)

            self.chefe.atualizar(self.jogador, self.paredes, dt, self.projeteis, self.perigos, self.raios, self.minions)
            for m in self.minions:
                m.atualizar(self.jogador, self.paredes, dt)

            for p in self.projeteis:
                p.atualizar()
            for pe in self.perigos:
                pe.atualizar(dt, self.jogador)
            for r in self.raios:
                r.atualizar(dt, self.jogador)

            # colisões: projétil do jogador -> chefe / servos
            for p in self.projeteis:
                if not p.vivo:
                    continue
                if p.dono == "jogador":
                    if self.chefe.vivo and math.hypot(p.x - self.chefe.x, p.y - self.chefe.y) < p.raio + self.chefe.raio:
                        self.chefe.receber_dano(p.dano)
                        p.vivo = False
                        continue
                    for m in self.minions:
                        if m.vivo and math.hypot(p.x - m.x, p.y - m.y) < p.raio + m.raio:
                            m.receber_dano(p.dano)
                            p.vivo = False
                            break
                else:
                    if math.hypot(p.x - self.jogador.x, p.y - self.jogador.y) < p.raio + self.jogador.raio:
                        self.jogador.receber_dano(p.dano)
                        p.vivo = False

            self.projeteis = [p for p in self.projeteis if p.vivo]
            self.perigos = [pe for pe in self.perigos if pe.vivo]
            self.raios = [r for r in self.raios if r.vivo]
            self.minions = [m for m in self.minions if m.vivo]

            if self.mensagem_timer > 0:
                self.mensagem_timer -= dt

            if self.jogador.vida <= 0:
                self.estado = "GAME_OVER"
                return

            if not self.chefe.vivo:
                self.pontuacao += 100 * (self.indice_chefe + 1)
                if self.indice_chefe + 1 >= len(LISTA_CHEFES):
                    self.estado = "VITORIA"
                else:
                    self.estado = "CHEFE_DERROTADO"
                    self.mensagem = f"{self.chefe.nome} DERROTADO!"
                    self.mensagem_timer = 2.2

        elif self.estado == "CHEFE_DERROTADO":
            if self.mensagem_timer > 0:
                self.mensagem_timer -= dt
            else:
                self.carregar_chefe(self.indice_chefe + 1)
                self.estado = "LUTANDO"

    # ------------------------------------------------------------------
    def desenhar_arena(self):
        self.tela.fill(FUNDO)
        for gx in range(0, LARGURA, 40):
            pygame.draw.line(self.tela, FUNDO_GRADE, (gx, HUD_ALTURA), (gx, ALTURA), 1)
        for gy in range(HUD_ALTURA, ALTURA, 40):
            pygame.draw.line(self.tela, FUNDO_GRADE, (0, gy), (LARGURA, gy), 1)

        for parede in self.paredes:
            pygame.draw.rect(self.tela, CINZA, parede)
            pygame.draw.rect(self.tela, (40, 40, 48), parede, 2)

        for pe in self.perigos:
            pe.desenhar(self.tela)
        for r in self.raios:
            r.desenhar(self.tela)
        for m in self.minions:
            m.desenhar(self.tela)
        if self.chefe.vivo:
            self.chefe.desenhar(self.tela)
        for p in self.projeteis:
            p.desenhar(self.tela)
        self.jogador.desenhar(self.tela)

    def desenhar_hud(self):
        pygame.draw.rect(self.tela, (18, 16, 22), (0, 0, LARGURA, HUD_ALTURA))
        pygame.draw.line(self.tela, DOURADO, (0, HUD_ALTURA), (LARGURA, HUD_ALTURA), 2)

        bx, by, bw, bh = 20, 16, 200, 22
        pygame.draw.rect(self.tela, VERMELHO_ESCURO, (bx, by, bw, bh))
        vida_pct = max(0, self.jogador.vida) / self.jogador.vida_max
        pygame.draw.rect(self.tela, VERMELHO, (bx, by, int(bw * vida_pct), bh))
        pygame.draw.rect(self.tela, BRANCO, (bx, by, bw, bh), 2)
        txt_vida = self.fonte_pequena.render(f"{max(0, int(self.jogador.vida))}/{self.jogador.vida_max}", True, BRANCO)
        self.tela.blit(txt_vida, (bx + bw // 2 - 22, by + 1))

        pronto = self.jogador.tempo_desde_dash >= self.jogador.dash_cooldown
        cor_dash = VERDE if pronto else CINZA_CLARO
        txt_dash = self.fonte_pequena.render("DASH pronto" if pronto else "dash...", True, cor_dash)
        self.tela.blit(txt_dash, (bx, by + bh + 3))

        txt_pontos = self.fonte_pequena.render(f"Pontos: {self.pontuacao}", True, DOURADO)
        self.tela.blit(txt_pontos, (LARGURA - 160, 10))
        txt_indice = self.fonte_pequena.render(f"Chefe {self.indice_chefe + 1}/5", True, BRANCO)
        self.tela.blit(txt_indice, (LARGURA - 160, 32))

        if self.chefe.vivo:
            nome = self.fonte_media.render(self.chefe.nome, True, BRANCO)
            self.tela.blit(nome, nome.get_rect(center=(LARGURA // 2, 16)))
            bx2, by2, bw2, bh2 = LARGURA // 2 - 220, 38, 440, 14
            pygame.draw.rect(self.tela, VERMELHO_ESCURO, (bx2, by2, bw2, bh2))
            pct = max(0, self.chefe.vida) / self.chefe.vida_max
            pygame.draw.rect(self.tela, LARANJA, (bx2, by2, int(bw2 * pct), bh2))
            pygame.draw.rect(self.tela, BRANCO, (bx2, by2, bw2, bh2), 1)

        if self.mensagem_timer > 0 and getattr(self, "mensagem", ""):
            txt = self.fonte_grande.render(self.mensagem, True, DOURADO)
            rect = txt.get_rect(center=(LARGURA // 2, ALTURA // 2))
            fundo = pygame.Surface((rect.width + 40, rect.height + 20), pygame.SRCALPHA)
            fundo.fill((0, 0, 0, 150))
            self.tela.blit(fundo, (rect.x - 20, rect.y - 10))
            self.tela.blit(txt, rect)

    def desenhar_menu(self):
        self.tela.fill(PRETO)
        titulo = self.fonte_grande.render("BOSS RUSH", True, DOURADO)
        self.tela.blit(titulo, titulo.get_rect(center=(LARGURA // 2, 100)))
        subt = self.fonte_media.render("5 chefes. Nenhuma chance de descanso.", True, BRANCO)
        self.tela.blit(subt, subt.get_rect(center=(LARGURA // 2, 150)))

        for i, cls in enumerate(LISTA_CHEFES):
            txt = self.fonte_pequena.render(f"{i + 1}. {cls.nome}", True, CINZA_CLARO)
            self.tela.blit(txt, txt.get_rect(center=(LARGURA // 2, 210 + i * 26)))

        linhas = [
            "WASD ou Setas: mover   |   Mouse: mirar   |   Botão esquerdo: atirar",
            "ESPAÇO ou SHIFT: dash (fica invulnerável por um instante)",
            "A vida é restaurada por completo entre um chefe e outro",
            "",
            "Pressione ENTER para começar",
        ]
        for i, linha in enumerate(linhas):
            txt = self.fonte_pequena.render(linha, True, CINZA_CLARO)
            self.tela.blit(txt, txt.get_rect(center=(LARGURA // 2, 400 + i * 28)))

    def desenhar_fim(self, venceu):
        self.tela.fill(PRETO)
        if venceu:
            titulo = self.fonte_grande.render("TODOS OS CHEFES DERROTADOS!", True, VERDE)
        else:
            titulo = self.fonte_grande.render("VOCÊ CAIU EM COMBATE", True, VERMELHO)
        self.tela.blit(titulo, titulo.get_rect(center=(LARGURA // 2, ALTURA // 2 - 80)))

        if not venceu:
            sub = self.fonte_media.render(f"Derrotado por: {self.chefe.nome}", True, CINZA_CLARO)
            self.tela.blit(sub, sub.get_rect(center=(LARGURA // 2, ALTURA // 2 - 30)))

        pts = self.fonte_media.render(f"Pontuação: {self.pontuacao}", True, BRANCO)
        self.tela.blit(pts, pts.get_rect(center=(LARGURA // 2, ALTURA // 2 + 15)))

        dica_texto = "Pressione R para tentar de novo" if not venceu else "Pressione R para jogar novamente"
        dica = self.fonte_pequena.render(dica_texto, True, CINZA_CLARO)
        self.tela.blit(dica, dica.get_rect(center=(LARGURA // 2, ALTURA // 2 + 65)))

    def desenhar(self):
        if self.estado == "MENU":
            self.desenhar_menu()
        elif self.estado in ("LUTANDO", "CHEFE_DERROTADO"):
            self.desenhar_arena()
            self.desenhar_hud()
        elif self.estado == "GAME_OVER":
            self.desenhar_fim(False)
        elif self.estado == "VITORIA":
            self.desenhar_fim(True)
        pygame.display.flip()

    # ------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.relogio.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.tratar_evento(ev)
            self.atualizar(dt)
            self.desenhar()


if __name__ == "__main__":
    Jogo().run()