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

import random

def makeName(kind, nodes, sort=True):
    if sort:
        return "%s(%s)" % (kind, ", ".join(sorted([x.getName() for x in nodes])))
    else:
        return "%s(%s)" % (kind, ", ".join([x.getName() for x in nodes]))

def safeDivide(a,b,c=0.0):
    if b != 0: return a/b
    else: return c

class Node:
    def __init__(self, name=None, inputs=None, outputs=None, permanent=False, virtual=False):
        self.name = name
        self.active = False
        self.previousActive = False
        self.pendingPreviousActive = False
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.actions = []
        self.time = 0
        self.activations = 0
        self.createdAt = 0
        self.topActive = False
        self.permanent=permanent
        self.network = None
        self.virtual = virtual
        self.rewardHistory = []
        for node in self.inputs:
            node.addOutput(self)

    def getName(self):
        return self.name

    def getId(self):
        return id(self)

    def isVirtual(self):
        return self.virtual

    # Return true if 'node' a child of self, or current node.
    # TODO: Rename?
    def isParent(self, node):
        if self == node: return True
        for x in self.inputs:
            if x.isParent(node): return True
        return False

    # Evaluate/Propagate this node.
    def tick(self, time):
        if self.time >= time:
            return False
        self.time = time
        self.pendingPreviousActive = self.active
        self.active = False
        for node in self.inputs:
            node.tick(time)
        return True

    def setNetwork(self, network):
        self.network = network
        self.createdAt = network.getTime()
        self.n_id = network.getNodeCount()

        # TODO: Evaluate if we shouldn't add all actions by default?
        for motor in network.motors:
            self.createAction(motor)

    def addOutput(self, node):
        if node not in self.outputs:
            self.outputs.append(node)

    # TODO: Should we handle previousActive here, or in tick?
    # Does previousActive mean it was active the previous tick, or should a node
    # be able to remain active until it's updated again. Stochastic updates?
    # For the future...
    def activate(self, time):
        if self.time <= time:
            self.active = True
            self.time = time
            self.activations = self.activations + 1

    def deactivate(self, time):
        if self.time <= time:
            self.active = False
            self.time = time

    def hasAction(self, motor):
        return self.findAction(motor) != None

    def getR(self, motor):
        return self.findAction(motor).getR()

    def findAction(self, motor):
        for a in self.actions:
            if a.motor.name == motor: return a
        return None

    def createAction(self, motor, reward=None):
        if self.findAction(motor): return self.findAction(motor)
        action = self.network.createAction(self, motor, reward)
        self.actions.append(action)
        return action

    def isActive(self):
        return self.active

    def wasActive(self):
        return self.previousActive

    def isTopNode(self, includeVirtual=False):
        if includeVirtual==False and self.virtual:
            return False
        else:
            return len([x for x in self.outputs if not x.isVirtual()]) == 0

    def isTopActive(self, includeVirtual=False):
        if includeVirtual==False and self.virtual:
            return False
        else:
            return self.topActive

    def realOutputs(self):
        return [x for x in self.outputs if not x.isVirtual()]

    # Utility function used by network to find topActive nodes when propagating.
    # Traverse tree from bottom to top (sensors => topnodes), depth first
    def _findTopActive(self, verbose=False):
        found = False
        for node in self.realOutputs():
            found = node._findTopActive(verbose) or found
        if found:
            return True
        elif self.active:
            self.topActive = True
        return self.topActive

    def updateQ(self, motor, reward, Qst1a):
        print "Node updateQ", self.name, motor, reward, Qst1a
        self.rewardHistory.append(reward)
        if len(self.rewardHistory) > self.network.config.max_reward_history:
            del self.rewardHistory[0]

        action = self.findAction(motor)
        action.updateQ(reward, Qst1a)

    def getQ(self):
        Q = {}
        for a in self.actions:
            if a.triggers == 0:
                continue
            for need in self.network.objectives:
                Q[need] = max(Q.get(need,a.getQ(need)), a.getQ(need))
        return Q

    def desc(self):
        return "%s = %s %d %d %d\n\t%s" % (self.getName(), self.active, self.activations, self.time-self.createdAt, len(self.actions), ",\n".join([x.desc() for x in self.actions]))

    def d(self):
        return (self.getName(), {'virtual':self.virtual, 'active':self.active, 'activations':self.activations, 'age':self.time-self.createdAt, 'numTriggers':self.getNumTriggers(), 'numActions':self.getNumActions(), 'Q':self.getQ(), 'actions':dict([a.d() for a in sorted(self.actions, key=lambda x:x.triggers)])})

    def getAge(self):
        return self.time-self.createdAt

    def getNumActions(self):
        return len(self.actions)

    def getNumTriggers(self):
        return sum([a.triggers for a in self.actions])

    def makeReal(self):
        self.virtual = False
