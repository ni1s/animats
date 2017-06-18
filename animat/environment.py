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
import errno
import datetime
import itertools
import random
from network import *
from agent import *
from sensor import *
from gradient_sensor import *
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
        self.movement = conf.get("movement", {})
        self.outputPath = os.path.join('output', datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f"))
        createPath(self.outputPath)

class Environment:
    def __init__(self, config=None, objectives=None, agent=None):
        self.config = config
        self.agent = agent
        self.objectives = objectives or config.objectives
        if self.config.enable_playback:
            self.playback = open( os.path.join(config.outputPath, "playback_script.py"), "w")
            print >> self.playback, "import turtle;wn = turtle.Screen();t = turtle.Turtle();t.setheading(90)"
            self.first_playback = True

    def endPlayback(self):
        if self.config.enable_playback:
            print >> self.playback, "wn.exitonclick()"
            print "Closing playback file"
            self.playback.close()

    def _playback(self, agent, action, nx=0, ny=0):
        if self.config.enable_playback:
            ulc = (-100,100) # upper-left corner coordinates
            if self.first_playback:
                print >> self.playback, "t.speed(0);t.hideturtle()"
                for y_pos in range(len(self.world)):
                    for x_pos in range(len(self.world[y_pos])):
                        if self.world[y_pos][x_pos] == 'f':
                            print >> self.playback, "t.penup();t.color((1,1,0));t.setpos(%d,%d);t.pendown();t.dot(5)" % (ulc[0]+10*x_pos, ulc[1]-10*y_pos)
                        elif self.world[y_pos][x_pos] == 'p':
                            print >> self.playback, "t.penup();t.color((1,0,0));t.setpos(%d,%d);t.pendown();t.dot(5)" % (ulc[0]+10*x_pos, ulc[1]-10*y_pos)

                print >> self.playback, "t.color((0,0,0));t.penup();t.setpos(%d,%d);t.setheading(%d);t.pendown();t.speed(6);t.showturtle()" % (ulc[0]+9*10, ulc[1]+9*(-10), 90)

                self.first_playback = False

            if action == 'up' or action == 'down' or action == 'right' or action == 'left':
                x,y = agent.position
                wrap = False
                if abs(nx-x) > 1 or abs(ny-y) > 1:
                    wrap = True
                if wrap: print >> self.playback, "t.color((1,0,0));t.dot(3);t.penup()"
                if self.config.is_torus:
                    nx = nx%self.getWidth()
                    ny = ny%self.getHeight()
                print >> self.playback, "t.setpos(%d,%d)" % (ulc[0]+nx*10, ulc[1]+ny*(-10))
                if wrap: print >> self.playback, "t.pendown();t.color((1,1,0));t.dot(3);t.color((0,0,0))"
            elif action == 'turn_right':
                print >> self.playback, "t.right(45)"
            elif action == 'turn_left':
                print >> self.playback, "t.left(45)"
            elif action == 'eat':
                print >> self.playback, "t.color((0,1,0));t.dot(5);t.color((0,0,0))"
            elif action == 'drink':
                print >> self.playback, "t.color((0,0,1));t.dot(5);t.color((0,0,0))"
            self.playback.flush()

    def endPlayback(self):
        if self.config.enable_playback:
            self.playback.flush()
            self.playback.close()

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

    def getCell(self, x, y):
        return self.world[y][x]

    # Create a basic network that supports this environment
    def createNetwork(self, conf):
        sensors = [SensorNode("$"+sensor, sensor, self) for sensor in conf.world_sensors]
        for sensor in conf.gradient_sensors:
            sensors.append(GradientSensorNode("$"+sensor, sensor, self))
        for sensor in conf.agent_sensors:
            sensors.append(ProprioceptorNode("$"+sensor, sensor))
        motors = [Motor(motor) for motor in conf.motors] #, 'wait']]
        return Network(conf, sensors, motors, self.objectives)

    def createAgent(self, conf):
        self.agent = Agent(conf, self, self.createNetwork(conf.network), {k:1 for k in self.objectives}, (9,9))
        for sensor in self.agent.network.sensors:
            sensor.addAgent(self.agent)
        return self.agent

    def _getCellReward(self, action, cell, status):
        rm = self.config.rewardMatrix
        am = rm.get(action, rm.get('*',{}))
        r = am.get(cell, am.get(self.agent.state, am.get('*',0.0)))
        reward = makeRewardDict(r, status)
        # TODO: truncate reward if need is satisfied
        return reward

    # This code is speecific for calculating the reward in the bee example
    def _getChangeReward(self, action, cell, status):
        if cell == "f":
            r = {self.objectives[0]:0.1}
        else:
            r = {self.objectives[-1]:0.0}
            for sensor in self.agent.network.sensors:
                if isinstance(sensor, GradientSensorNode) and sensor.active:
                    r[self.objectives[-1]] += sensor.getGradientSensorReward()
        reward = makeRewardDict(r, status)
        # TODO: truncate reward if need is satisfied
        return reward

    def takeAction(self, agent, action):
        cell = self.currentCell()
        cell_reward = self._getCellReward(action, cell, agent.needs)
        print "POSITION", agent.position, action

        def move_agent(agent, dx, dy):
#            print "PP MOVE", agent.position, dx, dy
            nx = agent.position[0]+dx
            ny = agent.position[1]+dy
            if self.config.is_torus:
                nx = nx%self.getWidth()
                ny = ny%self.getHeight()
            self._playback(agent, base_action, nx, ny)
            if nx >= 0 and nx < self.getWidth() and ny >= 0 and ny < self.getHeight():
                agent.position = (nx, ny)
#            print "PP NEW", agent.position

        # check if there is a rule how to translate the selected agent action into an agent movement
        if type(self.config.movement) == dict:
            action_states = self.config.movement.get(action, None)
            if type(action_states) is dict:
                # if there is a match for the current action then select the corresponding base action
                # and if there was no match for the current action, check for a match for the current cell
                base_actions = action_states.get(agent.state, action_states.get(cell, None))
            else:
                base_actions = action
        else:
            # there was no 'movement' configuration, use the action as a base state
            base_actions = action

        if type(base_actions) is not list:
            base_actions = [base_actions]

        for base_action in base_actions:
            if base_action == 'up':
                dx,dy = ORIENTATION_MATRIX[agent.orientation%8]
                move_agent(agent, dx, dy)
            elif base_action == 'down':
                dx,dy = ORIENTATION_MATRIX[(agent.orientation+4)%8]
                move_agent(agent, dx, dy)
            elif base_action == 'left':
                dx,dy = ORIENTATION_MATRIX[(agent.orientation-2)%8]
                move_agent(agent, dx, dy)
            elif base_action == 'right':
                dx,dy = ORIENTATION_MATRIX[(agent.orientation+2)%8]
                move_agent(agent, dx, dy)
            elif base_action == 'turn_right':
                agent.orientation = (agent.orientation+1)%8
                self._playback(agent, 'turn_right')
            elif base_action == 'turn_left':
                agent.orientation = (agent.orientation-1)%8
                self._playback(agent, 'turn_left')
            elif base_action == 'eat':
                self._playback(agent, action)
            elif base_action == 'drink':
                self._playback(agent, action)
            else:
                self._playback(agent, action)

#       This code is specific for te bee example
        cell = self.currentCell()
        if cell == 'f':
            self._playback(agent, 'eat')
        remote_reward = self._getChangeReward(action, cell, agent.needs)
        reward = {k:cell_reward.get(k, 0) + remote_reward.get(k, 0) for k in agent.needs.keys()}
        print "REWARD", reward
        print "ORIENTATION", agent.orientation

        trans = self.config.transform.get(action,{}).get(cell, None)
        if trans:
            print "*** TRANSFORM", action, cell, trans
            self.setCurrentCell(trans)

        return reward

    def printWorld(self):
        for row in self.world:
            print row
