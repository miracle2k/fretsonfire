#####################################################################
# -*- coding: iso-8859-1 -*-                                        #
#                                                                   #
# Frets on Fire                                                     #
# Copyright (C) 2006 Sami Kyöstilä                                  #
#                                                                   #
# This program is free software; you can redistribute it and/or     #
# modify it under the terms of the GNU General Public License       #
# as published by the Free Software Foundation; either version 2    #
# of the License, or (at your option) any later version.            #
#                                                                   #
# This program is distributed in the hope that it will be useful,   #
# but WITHOUT ANY WARRANTY; without even the implied warranty of    #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the     #
# GNU General Public License for more details.                      #
#                                                                   #
# You should have received a copy of the GNU General Public License #
# along with this program; if not, write to the Free Software       #
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,        #
# MA  02110-1301, USA.                                              #
#####################################################################

import pygame
import Log
import Audio

from Task import Task
from Player import Controls

class KeyListener:
  def keyPressed(self, key, unicode):
    pass
    
  def keyReleased(self, key):
    pass

class MouseListener:
  def mouseButtonPressed(self, button, pos):
    pass
    
  def mouseButtonReleased(self, button, pos):
    pass
    
  def mouseMoved(self, pos, rel):
    pass
    
class SystemEventListener:
  def screenResized(self, size):
    pass
    
  def restartRequested(self):
    pass
    
  def musicFinished(self):
    pass
    
  def quit(self):
    pass

MusicFinished = pygame.USEREVENT

try:
  reversed
except:
  def reversed(seq):
    seq = seq[:]
    seq.reverse()
    return seq

class Input(Task):
  def __init__(self):
    Task.__init__(self)
    self.mouse                = pygame.mouse
    self.mouseListeners       = []
    self.keyListeners         = []
    self.systemListeners      = []
    self.priorityKeyListeners = []
    self.controls             = Controls()
    self.disableKeyRepeat()

    # Initialize joysticks
    pygame.joystick.init()
    self.joystickAxes = {}
    self.joystickHats = {}

    self.joysticks = [pygame.joystick.Joystick(id) for id in range(pygame.joystick.get_count())]
    for j in self.joysticks:
      j.init()
      self.joystickAxes[j.get_id()] = [0] * j.get_numaxes() 
      self.joystickHats[j.get_id()] = [(0, 0)] * j.get_numhats() 
    Log.debug("%d joysticks found." % (len(self.joysticks)))

    # Enable music events
    Audio.Music.setEndEvent(MusicFinished)

    # Custom key names
    self.getSystemKeyName = pygame.key.name
    pygame.key.name       = self.getKeyName

  def reloadControls(self):
    self.controls = Controls()

  def disableKeyRepeat(self):
    pygame.key.set_repeat(0, 0)

  def enableKeyRepeat(self):
    pygame.key.set_repeat(300, 30)

  def addMouseListener(self, listener):
    if not listener in self.mouseListeners:
      self.mouseListeners.append(listener)

  def removeMouseListener(self, listener):
    if listener in self.mouseListeners:
      self.mouseListeners.remove(listener)

  def addKeyListener(self, listener, priority = False):
    if priority:
      if not listener in self.priorityKeyListeners:
        self.priorityKeyListeners.append(listener)
    else:
      if not listener in self.keyListeners:
        self.keyListeners.append(listener)

  def removeKeyListener(self, listener):
    if listener in self.keyListeners:
      self.keyListeners.remove(listener)
    if listener in self.priorityKeyListeners:
      self.priorityKeyListeners.remove(listener)

  def addSystemEventListener(self, listener):
    if not listener in self.systemListeners:
      self.systemListeners.append(listener)
      
  def removeSystemEventListener(self, listener):
    if listener in self.systemListeners:
      self.systemListeners.remove(listener)
      
  def broadcastEvent(self, listeners, function, *args):
    for l in reversed(listeners):
      if getattr(l, function)(*args):
        return True
    else:
      return False
    
  def broadcastSystemEvent(self, name, *args):
    return self.broadcastEvent(self.systemListeners, name, *args)

  def encodeJoystickButton(self, joystick, button):
    return 0x10000 + (joystick << 8) + button

  def encodeJoystickAxis(self, joystick, axis, end):
    return 0x20000 + (joystick << 8) + (axis << 4) + end
  
  def encodeJoystickHat(self, joystick, hat, pos):
    v = int((pos[1] + 1) * 3 + (pos[0] + 1))
    return 0x30000 + (joystick << 8) + (hat << 4) + v 
  
  def decodeJoystickButton(self, id):
    id -= 0x10000
    return (id >> 8, id & 0xff)

  def decodeJoystickAxis(self, id):
    id -= 0x20000
    return (id >> 8, (id >> 4) & 0xf, id & 0xf)

  def decodeJoystickHat(self, id):
    id -= 0x30000
    v = id & 0xf
    x, y = (v % 3) - 1, (v / 3) - 1
    return (id >> 8, (id >> 4) & 0xf, (x, y))

  def getKeyName(self, id):
    if id >= 0x30000:
      joy, axis, pos = self.decodeJoystickHat(id)
      return "Joy #%d, hat %d %s" % (joy + 1, axis, pos)
    elif id >= 0x20000:
      joy, axis, end = self.decodeJoystickAxis(id)
      return "Joy #%d, axis %d %s" % (joy + 1, axis, (end == 1) and "high" or "low")
    elif id >= 0x10000:
      joy, but = self.decodeJoystickButton(id)
      return "Joy #%d, %s" % (joy + 1, chr(ord('A') + but))
    return self.getSystemKeyName(id)

  def run(self, ticks):
    pygame.event.pump()
    for event in pygame.event.get():
      if event.type == pygame.KEYDOWN:
        if not self.broadcastEvent(self.priorityKeyListeners, "keyPressed", event.key, event.unicode):
          self.broadcastEvent(self.keyListeners, "keyPressed", event.key, event.unicode)
      elif event.type == pygame.KEYUP:
        if not self.broadcastEvent(self.priorityKeyListeners, "keyReleased", event.key):
          self.broadcastEvent(self.keyListeners, "keyReleased", event.key)
      elif event.type == pygame.MOUSEMOTION:
        self.broadcastEvent(self.mouseListeners, "mouseMoved", event.pos, event.rel)
      elif event.type == pygame.MOUSEBUTTONDOWN:
        self.broadcastEvent(self.mouseListeners, "mouseButtonPressed", event.button, event.pos)
      elif event.type == pygame.MOUSEBUTTONUP:
        self.broadcastEvent(self.mouseListeners, "mouseButtonReleased", event.button, event.pos)
      elif event.type == pygame.VIDEORESIZE:
        self.broadcastEvent(self.systemListeners, "screenResized", event.size)
      elif event.type == pygame.QUIT:
        self.broadcastEvent(self.systemListeners, "quit")
      elif event.type == MusicFinished:
        self.broadcastEvent(self.systemListeners, "musicFinished")
      elif event.type == pygame.JOYBUTTONDOWN: # joystick buttons masquerade as keyboard events
        id = self.encodeJoystickButton(event.joy, event.button)
        if not self.broadcastEvent(self.priorityKeyListeners, "keyPressed", id, u'\x00'):
          self.broadcastEvent(self.keyListeners, "keyPressed", id, u'\x00')
      elif event.type == pygame.JOYBUTTONUP:
        id = self.encodeJoystickButton(event.joy, event.button)
        if not self.broadcastEvent(self.priorityKeyListeners, "keyReleased", id):
          self.broadcastEvent(self.keyListeners, "keyReleased", id)
      elif event.type == pygame.JOYAXISMOTION:
        try:
          threshold = .8
          state     = self.joystickAxes[event.joy][event.axis]
          keyEvent  = None

          if event.value > threshold and state != 1:
            self.joystickAxes[event.joy][event.axis] = 1
            keyEvent = "keyPressed"
            args     = (self.encodeJoystickAxis(event.joy, event.axis, 1), u'\x00')
            state    = 1
          elif event.value < -threshold and state != -1:
            keyEvent = "keyPressed"
            args     = (self.encodeJoystickAxis(event.joy, event.axis, 0), u'\x00')
            state    = -1
          elif state != 0:
            keyEvent = "keyReleased"
            args     = (self.encodeJoystickAxis(event.joy, event.axis, (state == 1) and 1 or 0), )
            state    = 0

          if keyEvent:
            self.joystickAxes[event.joy][event.axis] = state
            if not self.broadcastEvent(self.priorityKeyListeners, keyEvent, *args):
              self.broadcastEvent(self.keyListeners, keyEvent, *args)
        except KeyError:
          pass
      elif event.type == pygame.JOYHATMOTION:
        try:
          state     = self.joystickHats[event.joy][event.hat]
          keyEvent  = None

          # When using the GH2 PS2 controller in conjunction with a Logic3
          # "PS2 to PS3 converter" it is impossible to pick the first fret.
          # This may be a bug in PyGame, or generally a problem with that
          # particular adapter, I'm not sure. Specifically, the following
          # happens:
          #     * If fret 1 (joy button 7) is pressed and you pick, a
          #       JOYBUTTONUP event for the fret is first added to the
          #       PyGame event queue, then the JOYHATMOTION event second.
          #       When the pick is released, we automatically get a
          #       JOYBUTTONDOWN event for the still pressed fret.
          #     * If you press fret 1 while the pick is pressed, you will
          #       see (careful, this is from memory): A fret 1 JOYBUTTONUP,
          #       a fret 1 JOYBUTTONDOWN immediately afterwards, followed by
          #       a JOYHATMOTION releasing the pick. Releasing the fret
          #       again while maintaining the pick will result in another
          #       JOYHATMOTION again, bringing the pick back.
          #       This issue is currently NOT FIXED by this workaround! In
          #       fact, *due* to the workaround, if you press and release
          #       fret 1 while picking, the fret will be registered as UP
          #       even though it is not actually pressed. This is very seldom
          #       a problem during play though.
          #     * In both those cases (that involve the first fret), we
          #       actually get a different JOYHATMOTION event than in the
          #       "normal" case: (1,0) instead of (0,-1) and (-1,0) instead
          #       of (0,1). This is actually fortunate, since it allows us
          #       to detect the situation and fix the fret 1 issue as well.
          if event.value == (1,0) or event.value == (-1,0):
            # rewrite the value of the hat event
            if event.value == (1,0): final_event_value = (0,-1)
            elif event.value == (-1,0): final_event_value = (0,1)
            # as explained, we know that the player has button 7 pressed,
            # but a previous event set it to UP. we fix this by simply
            # re-issuing a "keyPressed" event.
            id = self.encodeJoystickButton(event.joy, 7)
            if not self.broadcastEvent(self.priorityKeyListeners, "keyPressed", id, u'\x00'):
              self.broadcastEvent(self.keyListeners, "keyPressed", id, u'\x00')
          else:
            final_event_value = event.value

          if event.value != (0, 0) and state == (0, 0):
            self.joystickHats[event.joy][event.hat] = final_event_value
            keyEvent = "keyPressed"
            args     = (self.encodeJoystickHat(event.joy, event.hat, final_event_value), u'\x00')
            state    = final_event_value
          else:
            keyEvent = "keyReleased"
            args     = (self.encodeJoystickHat(event.joy, event.hat, state), )
            state    = (0, 0)

          if keyEvent:
            self.joystickHats[event.joy][event.hat] = state
            if not self.broadcastEvent(self.priorityKeyListeners, keyEvent, *args):
              self.broadcastEvent(self.keyListeners, keyEvent, *args)
        except KeyError:
          pass
