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

import itertools
import random
from network import *
import environment
import nodes
import plotter
import math

def dist(a,b):
    return math.sqrt(sum([ pow(a.get(k,0) - b.get(k,0), 2.0) for k in a.keys()]))

def length(x):
    return math.sqrt(sum([v**2 for v in x.values()]))

def relative_surprise(a,b):
    l = min(max(length(a), 0.01), max(length(b), 0.01))
    return dist(a,b)/l

def averageDict( a, b, keys, sigma ):
    return {k:(1-sigma)*a.get(k,0)+sigma*b.get(k,0) for k in keys}

def wellbeeing_min(x, c):
    return min([max(c.get(k,-1e99), v) for k,v in x.items()])

def wellbeeing_prod(x, c):
    p = 1
    for k,v in x.items():
        p = p * max( c.get(k,-1e99), v )
    return p

WELLBEEING_FUNCTIONS = { 'min':wellbeeing_min, 'product':wellbeeing_prod }

class AgentConfig:
    def __init__(self, conf):
        self.network = NetworkConfig(conf.get("network", {}))
        self.surprise_const = conf.get("surprise_const", 2.0)
        self.wellbeeing_const = conf.get("wellbeeing_const", {})
        self.wellbeeing_function = conf.get("wellbeing_function", "min")
        self.PLOTTER_ENABLED = conf.get("PLOTTER_ENABLED", False)
        self.PLOTTER_EVERY_FRAME = conf.get("PLOTTER_EVERY_FRAME", False)
        self.features = conf.get("features", {})
        self.states = conf.get("states", {})
        self.state_change = conf.get("state change", {})

# y=0 up
# x=0 left
ORIENTATION_MATRIX = [(0,-1), (1,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1)]

class Agent:
    def __init__(self, config, environment, network, needs=None, position=(0,0), growthRate=0.01):
        self.config = config
        self.environment = environment
        self.position = position
        self.orientation = 0 # 0=up, 2=right, 4=down, 6=left
        self.network = network
        self.environment = environment
        self.growthRate = growthRate
        self.needs = needs or {need:1.0 for need in network.objectives}
        self.trail = []
        self.wellbeeingTrail = []
        self._learningData = None
        self._previousTopNodes = []
        self.surpriseMatrix = {}
        self.surpriseMatrix_SEQ = {}
        self._wellbeeingFunc = WELLBEEING_FUNCTIONS.get(config.wellbeeing_function)
        self.previousSensors = []
        if len(config.states) > 0:
            self.state = config.states[0] # start in the first state
        else:
            self.state = None

    def wellbeeing(self):
        return self._wellbeeingFunc(self.needs, self.config.wellbeeing_const)

    # This is the main learning loop for the Animat
    def tick(self):
        print
        print "TICK:", self.network.time
        print "NETWORK:", self.network.nodes.keys()

        # OBSERVE - Read new inputs and update Activation and Status
        self.network.tick()

        # Check if stimuly changed from previous frame, this is used to DECIDE
        # when to propagate "previous state" for SEQ nodes.
        if self.previousSensors != self.network.activeSensors():
            self.previousSensors = self.network.activeSensors()
            self.sensorsChanged = True
            print "SENSORS CHANGED", self.network.time
        else:
            self.sensorsChanged = False

        # Plot the network
        if self.config.PLOTTER_ENABLED:
            if self.config.PLOTTER_EVERY_FRAME or (self.network.lastChange == self.network.time-1 or self.network.time == 1):
                plotter.plot(self.network, self.environment.config.outputPath)

        # Learning began last tick, follow up with the new Q.
        self._endLearning()

        cell = self.environment.currentCell()

        print "CELL:", cell
        print "SENSORS:", ", ".join([x.name for x in self.network.activeSensors()])
        print "TOP:", ", ".join([x.name for x in self.network.topNodes()])
        print "TOP ACTIVE:", ", ".join([x.name for x in self.network.activeTopNodes()])
        print "PREVIOUS TOP ACTIVE:", ", ".join([x.name for x in self._previousTopNodes])
        print "ALL", ", ".join(["%s=%s" % (x.getName(), x.isActive() and "ON" or "OFF") for x in self.network.allNodes()])
        print "NEEDS:", self.needs

        # DECIDE - select ACTION for the node under attention that maximizes
        # expected lifespan (EXPLOIT) or tries a new state-action pair (EXPLORE)
        score,action,Q = self.network.getBestAction(self.needs)

#        print "KNOWN ACTIONS:", self.network.knownActions(need)

        if not action: return
        print "BEST ACTION:", action

        # take action
        prediction,numPredictions = self.network.predictR(action)
        reward = self.environment.takeAction(self, action)
        surprise = relative_surprise(prediction, reward)
        print ">>> SURPRISE", surprise, numPredictions, prediction, reward

        # agent state change caused by action
        new_state = self.config.state_change.get(action)
        if new_state != None and new_state != self.state:
            print "AGENT STATE CHANGE: '", self.state, "' -> '", new_state,"'"
            self.state = new_state

        self.trail.append( (cell, action) )
        self.wellbeeingTrail.append( self.wellbeeing() )
        print ">>> reward", cell, action, reward, prediction
        self._beginLearning(surprise, reward, action, prediction, numPredictions)

        # update status vector
        self._updateNeeds(reward)

    def mostUrgentNeed(self):
        # Get the need with the lowest value
        print "NEEDS", self.needs
        return sorted([(v,k) for k,v in self.needs.items()])[0][1]

    def _updateNeeds(self, deltaNeeds):
        if type(deltaNeeds) == dict:
            for k,v in deltaNeeds.items():
                if k != 'fear':
                    self.needs[k] = max( min(self.needs[k] + v, 1.0), 0)
        else: # it's a scalar, apply to all needs
            for k,v in self.needs.items():
                if k != 'fear':
                    self.needs[k] = max( min(v + deltaNeeds, 1.0), 0)

        print "Needs", self.needs

    def _updateSurpriseMatrix(self, surprise, reward, action, numPredictions):
        # Don't build on top of Virtual nodes
        print "_updateSurpriseMatrix", numPredictions
        topnodes = self.network.activeTopNodes(includeVirtual=False)

        for a,b in itertools.combinations(topnodes, 2):
            pP = self.surpriseMatrix.get((a.name, b.name), reward)
            self.surpriseMatrix[(a.name,b.name)] = averageDict( pP, reward, self.network.objectives, 0.5 )

        for a,b in itertools.product(self._previousTopNodes, topnodes):
            pP = self.surpriseMatrix_SEQ.get((a.name, b.name), reward)
            self.surpriseMatrix_SEQ[(a.name, b.name)] = averageDict( pP, reward, self.network.objectives, 0.1 )

        # TODO: only combine with the least surprised node?
        # then we have to calculate the best action, given status, for each nodes actions
        # and then relative_surprise given the expected reward
        if surprise > self.config.surprise_const and numPredictions > 2:
            surprises = sorted([(relative_surprise(node.getR(action), reward), node) for node in topnodes])
            xSurprises = sorted([(relative_surprise(v, reward), k, v) for k,v in self.surpriseMatrix.items()])
            # TODO: take the least surprised combination?
            if len(surprises) > 1 and self.config.features.get("AND", False):
                print "XXX", surprises
                _,a = leastSurprised = surprises[0]
                _,b = mostSurprised = surprises[-1]
                print "XXX most", mostSurprised
                print "XXX least", leastSurprised
                print "XXX xS", xSurprises
                # Don't add nodes with the same input, or one that shares the same forefather
                if a == b or a.isParent(b) or b.isParent(a) or self.network.hasAndNode([a,b]):
                    pass
                else:
                    n = nodes.AndNode(inputs=[a, b], virtual=False)
                    self.network.addNode(n)
                    # TODO: make sure it learns the correct action from the start.
                    # Since it's not a top-active node it will not get feedback.
                    # Check this...
                    n.updateQ(action, reward, environment.makeRewardDict(0, self.needs))
                    print ">>>> Grew a new AND-node", n.desc()
            elif self.config.features.get("SEQ", False):
                seqSurprises = sorted([(relative_surprise(v, reward), k) for k,v in self.surpriseMatrix_SEQ.items()])
                if len(seqSurprises) > 0:
                    a,b = seqSurprises[0][1]
                    a,b = self.network.findNode(a), self.network.findNode(b)
                    if seqSurprises[0][0] < 0.5 and not self.network.hasSeqNode([a,b]):
                        #if a.isParent(b) or b.isParent(a) or self.network.hasSeqNode([a,b]):
                        #continue
                        n = nodes.SEQNode(inputs=[a, b], virtual=False)
                        self.network.addNode(n)
                        n.updateQ(action, reward, environment.makeRewardDict(0, self.needs))
                        print ">>>> Grew a new SEQ-node", n.desc()

    def _beginLearning(self, surprise, reward, action, prediction, numPredictions):
        topnodes = self.network.activeTopNodes(includeVirtual=False)

        self._updateSurpriseMatrix(surprise, reward, action, numPredictions)
        self._learningData = {'nodes': topnodes, 'reward':reward, 'action': action, 'surprise':surprise, 'previousTop':self._previousTopNodes }

    def _endLearning(self):
        if not self._learningData: return

        nodes = self._learningData['nodes']
        motor = self._learningData['action']
        reward = self._learningData['reward']
        newTopnodes = self.network.activeTopNodes(includeVirtual=False)
        previousTop = self._learningData['previousTop']

        score,q_action,Q = self.network.getBestAction(self.needs, allowExploration=False, epsilon=0)
        Qst1a = {obj:x['weighted'] for obj,x in Q.items()}

        print ">>> END LEARNING", motor, reward, Qst1a, [x.getName() for x in nodes]

        # Learn casuality for all active top-nodes
        for node in nodes:
            node.updateQ(motor, reward, Qst1a)

        # For SEQ-learning
        if nodes != newTopnodes:
            self._previousTopNodes = nodes
        self._learningData = None

    # def _prune(self):
    #     # TODO: Don't prune sensors or first layer nand
    #     for n in self.network.topNodes():
    #         if n.getAge()>100 and n.getNumActions()<2 and n.getNumTriggers()<20:
    #             print "PRUNE", n.d()
    #             self.network.deleteNode(n)
    #
