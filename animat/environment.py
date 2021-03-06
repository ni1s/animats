# -*- coding: utf-8 -*-
#
#    pyAnimat - Simulate Animats using Transparent Graphs as a way to AGI
#    Copyright (C) 2017  Nils Svangård, Claes Strannegård
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os, os.path
import datetime
import itertools
import random
from network import *
from agent import *
from sensor import *
from motor import *

def makeRewardDict(reward, needs):
    if type(reward) != dict:
        reward = {k:reward for k in needs.keys()}
    return reward

def createPath(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


class EnvironmentConfig:
    def __init__(self, conf):
#        worldmap = "rrrrrrrrrr\ngggggggggg\n0000000000\nbbbbbbbbbb\nxxxxxxxxxx"
        self.world = [list(x) for x in conf.get("world").split("\n")]
        self.is_torus = conf.get("torus", False)
        self.enable_playback = conf.get("playback", False)
        self.objectives = conf.get("objectives", ["water", "glucose"])
        self.blocks = conf.get("blocks", {})
        self.rewardMatrix = conf.get("rewards", {})
        self.agent = AgentConfig(conf.get("agent"))
        self.maxIterations = conf.get("iterations", 100)
        self.transform = conf.get("transform", {})
        self.outputPath = os.path.join('output', datetime.datetime.now().isoformat())
        createPath(self.outputPath)

class Environment:
    def __init__(self, config=None, objectives=None, agent=None):
        self.config = config
        self.agent = agent
        self.objectives = objectives or config.objectives
        if self.config.enable_playback:
            self.playback = open( os.path.join(config.outputPath, "playback_script.py"), "w")
            print >> self.playback, "import turtle;t = turtle.Turtle()"

    def _playback(self, agent, action, nx=0, ny=0):
        if self.config.enable_playback:
            if action == 'up' or action == 'down' or action == 'right' or action == 'left':
                x,y = agent.position
                wrap = False
                if abs(nx-x) > 1 or abs(ny-y) > 1:
                    wrap = True
                if wrap: print >> self.playback, "t.color((1,0,0));t.dot(3);t.penup()"
                if self.config.is_torus:
                    nx = nx%self.getWidth()
                    ny = ny%self.getHeight()
                print >> self.playback, "t.setpos(%d,%d)" % (nx*10, ny*10)
                if wrap: print >> self.playback, "t.pendown();t.color((1,1,0));t.dot(3);t.color((0,0,0))"
            elif action == 'turn_right':
                print >> self.playback, "t.right(90)"
            elif action == 'turn_left':
                print >> self.playback, "t.left(90)"
            elif action == 'eat':
                print >> self.playback, "t.color((0,1,0));t.dot(5);t.color((0,0,0))"
            elif action == 'drink':
                print >> self.playback, "t.color((0,0,1));t.dot(5);t.color((0,0,0))"

    def setAgent(self, agent):
        self.agent = agent
        agent.setEnvironment(self)

    def tick(self):
        print "tick"
        self.agent.tick()

    def takeAction(self, agent, action):
        return None

    def createNetwork(self):
        return None

    def createAgent(self):
        return None

class VirtualEnvironment(Environment):
    def __init__(self, config):
        Environment.__init__(self, config)
        self.world = config.world

    def getHeight(self):
        return len(self.world)

    def getWidth(self):
        return len(self.world[0])

    def currentCell(self,delta=(0,0)):
        y = (self.agent.position[1]+delta[1]) % len(self.world)
        x = (self.agent.position[0]+delta[0]) % len(self.world[y])
        return self.world[y][x]

    def setCurrentCell(self, v):
        y = self.agent.position[1] % len(self.world)
        x = self.agent.position[0] % len(self.world[y])
        self.world[y][x] = v

    def readSensor(self, x, delta=(0,0)):
        if x == 't': return 1
        cell = self.currentCell(delta)
        observation = self.config.blocks.get(cell,{})
        return observation.get(x,0)

    # Create a basic network that supports this environment
    def createNetwork(self, conf):
        def makeSensor(env, cell, delta=(0,0)):
            return lambda t: env.readSensor(cell, delta)
        sensors = [SensorNode("$"+sensor, makeSensor(self, sensor)) for sensor in conf.sensors]
        motors = [Motor(motor) for motor in conf.motors] #, 'wait']]
        return Network(conf, sensors, motors, self.objectives)

    def createAgent(self, conf):
        self.agent = Agent(conf, self, self.createNetwork(conf.network), {k:1 for k in self.objectives}, (0,0))
        return self.agent

    def _getReward(self, action, cell, status):
        rm = self.config.rewardMatrix
        am = rm.get(action, rm.get('*',{}))
        r = am.get(cell, am.get('*',0.0))
        reward = makeRewardDict(r, status)
        # TODO: truncate reward if need is satisfied
        return reward

    def takeAction(self, agent, action):
        cell = self.currentCell()
        reward = self._getReward(action, cell, agent.needs)
        print "POSITION", agent.position, action

        def move_agent(agent, dx, dy):
#            print "PP MOVE", agent.position, dx, dy
            nx = agent.position[0]+dx
            ny = agent.position[1]+dy
            if self.config.is_torus:
                nx = nx%self.getWidth()
                ny = ny%self.getHeight()
            self._playback(agent, action, nx, ny)
            if nx >= 0 and nx < self.getWidth() and ny >= 0 and ny < self.getHeight():
                agent.position = (nx, ny)
#            print "PP NEW", agent.position

        if action == 'up':
            dx,dy = ORIENTATION_MATRIX[agent.orientation%8]
            move_agent(agent, dx, dy)
        elif action == 'down':
            dx,dy = ORIENTATION_MATRIX[(agent.orientation+4)%8]
            move_agent(agent, dx, dy)
        elif action == 'left':
            dx,dy = ORIENTATION_MATRIX[(agent.orientation-2)%8]
            move_agent(agent, dx, dy)
        elif action == 'right':
            dx,dy = ORIENTATION_MATRIX[(agent.orientation+2)%8]
            move_agent(agent, dx, dy)
        elif action == 'turn_right':
            agent.orientation = (agent.orientation+1)%8
            self._playback(agent, action)
        elif action == 'turn_left':
            agent.orientation = (agent.orientation-1)%8
            self._playback(agent, action)
        elif action == 'eat':
            self._playback(agent, action)
        elif action == 'drink':
            self._playback(agent, action)

        trans = self.config.transform.get(action,{}).get(cell, None)
        if trans:
            print "*** TRANSFORM", action, cell, trans
            self.setCurrentCell(trans)

        return reward

    def printWorld(self):
        for row in self.world:
            print row
