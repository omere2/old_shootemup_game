import pygame
from pygame.locals import *
import sys
import os
import random

SCREENSIZE = (800,600)
COLORKEY = (255,0,255,255)


# This is the object of the cursor (the gun)
class Aim:
    def __init__(self, fire_sound, reload_shot = 0, reload_clip = 0):
        # trigger = 0 when is not pressed. Nonautomatic guns cannot fire without
        # releasing the trigger
        self.trigger = 0 
        # sound associated with fire
        self.fire_sound = fire_sound 
        # reload time between every shot fired
        self.reload_shot_time = reload_shot
        # reload time for every clip
        self.reload_clip_time = reload_clip
        # last time the gun was fires
        self.last_fire = -10000

    def press_trigger(self, pos):
        if self.trigger == 0:
            current_time = pygame.time.get_ticks()
            if  current_time - self.last_fire >= self.reload_shot_time:
                self.last_fire = current_time
                self.trigger = 1
                self.fire_sound.play()
                return True
        return False

    def unpress_trigger(self):
        if self.trigger == 1:
            self.trigger = 0

    def action(self, mouse):
        if mouse.type == MOUSEBUTTONDOWN:
            if mouse.button == 1:
                self.press_trigger()
        if mouse.type == MOUSEBUTTONUP:
            if mouse.button == 1:
                self.unpress_trigger()

class AbstractEntity:
    def __init__(self, pos, ttl = -1):
        self.create_time = pygame.time.get_ticks()
        self.move_func = pos
        #self.pos = [pos[0], pos[1]]
        self.pos = self.move_func.get_pos()
        self.ttl = ttl
        self.alive = True;

    def on_die(self):
        pass
    
    def iterate(self):
        self.pos = self.move_func.get_pos(pygame.time.get_ticks())
        if self.alive == True and self.ttl != -1:
            if pygame.time.get_ticks() - self.create_time > self.ttl:
                self.alive = False
                self.on_die()
                
        

class Entity(AbstractEntity):
    def __init__(self, anim, pos, ttl = -1):
        AbstractEntity.__init__(self, pos, ttl)
        self.anim = anim
        self.alive = True

    # pixel collision detection
    def collision(self, pos):
        size = self.get_image().get_size()
        if pos[0] >= self.pos[0] and pos[0] < self.pos[0] + size[0] \
           and pos[1] >= self.pos[1] and pos[1] < self.pos[1] + size[1]: # rough detection
            if self.get_image().get_at((pos[0]-self.pos[0], pos[1]-self.pos[1])) != COLORKEY: # pixel detection
                return True
        return False

    def is_alive(self):
        return self.alive

    def get_image(self):
        return self.anim.get_image()

class FragileEntity(Entity):
    def __init__(self, anim, pos, ttl = -1):
        Entity.__init__(self, anim, pos, ttl)

    def collision(self, pos):
        global entities
        global gfx
        if Entity.collision(self, pos):
            self.alive = False
            entities.add(Entity(Animation(gfx["coolexplode"]), \
            Movement((self.pos[0]-gfx["coolexplode"].center[0]+self.anim.anim.center[0],self.pos[1]-gfx["coolexplode"].center[1]+self.anim.anim.center[1])), gfx["coolexplode"].cycle_time))
    def on_die(self):
        entities.add(Entity(Animation(gfx["explode"]), \
            Movement((self.pos[0]-gfx["explode"].center[0]+self.anim.anim.center[0],self.pos[1]-gfx["explode"].center[1]+self.anim.anim.center[1])), gfx["explode"].cycle_time))

class PictureSequence:
    def __init__(self, directory):
        self.anim = []
        self.cycle_time = -1
        self.repeat = 0
        self.alpha = 255        
        path = "./gfx/" + directory + "/"
        temp = dict()
        try:
            temp = dict([i.split() for i in open(path + "info.txt").readlines()])
        except:
            pass
        if temp.has_key("cycle_time"):
            self.cycle_time = int(temp["cycle_time"])
        if temp.has_key("repeat"):
            self.repeat = int(temp["repeat"])
        if temp.has_key("alpha"):
            self.alpha = int(temp["alpha"])
        # load animation pictures
        for s in os.listdir(path):
            if s.find(".png") != -1:
                i = pygame.image.load(path + s)
                i.set_colorkey(COLORKEY)
                i.set_alpha(self.alpha)
                self.anim.append(i)
        self.center = (self.anim[0].get_size()[0] / 2, self.anim[0].get_size()[1] / 2)
        self.seq = 0
        self.last_frame_time = 0

    def size(self):
        return len(self.anim)
    
    def __getitem__(self, i):
        return self.anim[i]
    
class Animation:
    def __init__(self, pic_seq):
        self.anim = pic_seq
        self.last_frame_time = 0
        self.seq = 0

        # fade properties
        self.fade_time = -1
        self.fade_start = 0
        self.org_alpha = self.anim.alpha
        self.cur_alpha = self.org_alpha
        self.dest_alpha = self.cur_alpha
        self.fade_diff = 0
        
    def get_image(self):
        cur_time = pygame.time.get_ticks()
        pic = self.anim[self.seq]
        # make new copy of image. When applying various effects it won't change the
        # original image
        pic = pic.convert(pic) 
        if cur_time - self.last_frame_time > self.anim.cycle_time / self.anim.size():
            self.last_frame_time = cur_time
            self.seq += 1
        if self.seq == self.anim.size():
            self.seq = 0

        # Handle fade
        if self.fade_time != -1:
            time_diff = pygame.time.get_ticks() - self.fade_start
            self.cur_alpha = self.dest_alpha + self.fade_diff - (time_diff * self.fade_diff) / self.fade_time
            if time_diff >= self.fade_time:
                self.cur_alpha = self.dest_alpha
                self.fade_time = -1
            
        pic.set_alpha(self.cur_alpha)
        return pic

    def fade(self, time = 1000, dest_alpha = 0):
        self.fade_start = pygame.time.get_ticks()
        self.fade_time = time
        if self.cur_alpha == dest_alpha:
            self.dest_alpha = self.org_alpha
        else:
            self.dest_alpha = dest_alpha
        self.fade_diff = self.cur_alpha - self.dest_alpha


class EntityManager:
    def __init__(self):
        self.entities = []
        self.newly_created = []
        self.newly_died = []

    def add(self, entity):
        print "Created:", entity
        self.newly_created += [entity]
        return entity
    def remove(self, entity):
        print "Died:", entity
        self.newly_died += [entity]
    def iteration(self):
        for e in self.entities:
            e.iterate()
            if e.alive == False:
                self.remove(e)
        for e in self.newly_died:
            self.entities.remove(e)
        self.entities += self.newly_created
        self.newly_created = []
        self.newly_died = []
    def __getitem__(self, i):
        return self.entities[i]
    def __len__(self):
        return len(self.entities)
            
class Movement:
    def __init__(self, start_pos):
        self.start_pos = start_pos

    def get_pos(self, time = 0):
        return self.start_pos

class MovementThrow(Movement):
    def __init__(self, start_pos, end_pos, time, gforce = 0.0001):
        Movement.__init__(self, start_pos)
        self.start_time = pygame.time.get_ticks()
        self.velocity = ((end_pos[0] - start_pos[0]) / float(time), (end_pos[1] - start_pos[1] - gforce * time * time) / time)
        self.gforce = gforce

    def get_pos(self, time = 0):
        if time == 0:
            return self.start_pos
        else:
            t = (float(time) - self.start_time)
            return (self.start_pos[0] + self.velocity[0]*t, self.start_pos[1] + self.velocity[1]*t + t*t*self.gforce)
        

def load_sounds():
    l = {}
    for s in os.listdir("./sounds"):
        l[s.split(".")[0]] = (pygame.mixer.Sound("./sounds/" + s))
    return l

def load_gfx():
    l = {}
    for s in os.listdir("./gfx"):
        #l[s.split(".")[0]] = (pygame.image.load("./gfx/" + s))
        l[s] = PictureSequence(s)
    return l


# init
pygame.init()
pygame.mixer.init()
sounds = load_sounds()
gfx = load_gfx()
screen = pygame.display.set_mode(SCREENSIZE)#, FULLSCREEN)
pygame.mouse.set_cursor(*pygame.cursors.broken_x)
entities = EntityManager()
#for i in xrange(10):
    #entities.add(FragileEntity(Animation(gfx["thing"]), (random.randint(0,640), random.randint(0,480)))) #1000+i*100))
#mov = Movement((random.randint(0,640), random.randint(0,480)))
#mov = MovementThrow((50,500), (600, 500), 2000)
#entities.add(FragileEntity(Animation(gfx["thing"]), mov)) #1000+i*100))
#interface = entities.add(Entity(Animation(gfx["interface"]), (0,500)))
#entities.add(Entity(Animation(gfx["interface"]), (400,500)))    
entities.iteration()

gun = Aim(fire_sound = sounds["gun"], reload_shot = 0)

pygame.time.set_timer(USEREVENT, 500)

while 1:
    screen.fill(0)
    
        
    if pygame.mouse.get_pressed()[0] == 1:
        mouse_pos = pygame.mouse.get_pos()
        if gun.press_trigger(mouse_pos):
            for e in entities:
                e.collision(mouse_pos)
    else:
        gun.unpress_trigger()

    entities.iteration()
        
    for event in pygame.event.get():
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                sys.exit()
            #if event.key == K_TAB:
             #   interface.anim.fade(1000, 50)
        if event.type == USEREVENT:
            mov = MovementThrow((50,random.randint(100,500)), (600, random.randint(100,500)), random.randint(2000, 3000))
            if random.randint(0,1) == 0:
                entities.add(FragileEntity(Animation(gfx["smiley"]), mov, 3000)) #1000+i*100))
            else:
                entities.add(FragileEntity(Animation(gfx["thing"]), mov, 3000)) #1000+i*100))
            
    for e in entities:
        screen.blit(e.get_image(), e.pos)
    pygame.display.flip()

#    pygame.event.pump()