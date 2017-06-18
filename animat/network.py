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
from pprint import pprint
from action import *
import node

def oneSum(a,b):
    return min(1, max(-1, a+b))

def mean(v):
    return sum(v)/len(v)

def weightedMean(v):
    a = sum([x*y for x,y in v])
    b = sum([y for _,y in v])
    if b == 0: return x
    else: return a/b


def _weighted_utility(Q, status):
    return sum([(1-v) * Q.get(k, 0.0) for k,v in status.items()])

def _safe_weighted_utility(Q, status):
    # multiply status with .75 to avoid fully satisfied needs take catastrophic actions
    return sum([(1-v*0.95) * Q.get(k, 0.0) for k,v in status.items()])

def _min_utility(Q, status):
    return min([v+Q.get(k, 0.0) for k,v in status.items()])

def _true_min_utility(Q, status):
    return min([Q.get(k, 0.0) for k,v in status.items()])

UTILITY_FUNCTIONS = {}
UTILITY_FUNCTIONS["weighted"] = _weighted_utility
UTILITY_FUNCTIONS["safe_weighted"] = _safe_weighted_utility
UTILITY_FUNCTIONS["min"] = _true_min_utility
UTILITY_FUNCTIONS["min+"] = _min_utility

def _wellbeeing(status):
    return min(status.values())

def _q_map_linear(Q, status):
    w = _wellbeeing(status)
    return w * Q['min'] + (1-w) * Q['max']

def _q_map_fitted(Q, status):
    # TODO: make it smooth interpolated
    w = _wellbeeing(status)
    c = 0.75
    if w < c:
        w = w/c
        return w * Q['weighted'] + (1-w) * Q['max']
    else:
        w = (w-c)/c
        return w * Q['max'] + (1-w) * Q['weighted']

Q_FUNCTIONS = {}
Q_FUNCTIONS['min'] = lambda Q, status: Q['min']
Q_FUNCTIONS['max'] = lambda Q, status: Q['max']
Q_FUNCTIONS['mean'] = lambda Q, status: Q['mean']
Q_FUNCTIONS['weighted'] = lambda Q, status: Q['weighted']
Q_FUNCTIONS['linear'] = _q_map_linear
Q_FUNCTIONS['fitted'] = _q_map_fitted

class NetworkConfig:
    def __init__(self, conf):
        self.epsilon = conf.get("epsilon", 0.1)
        self.utility_function = conf.get("utility_function", "weighted")
        self.q_function = conf.get("q_function", "weighted")
        self.max_reward_history = conf.get("max_reward_history", 10)
        self.q_learning_factor = conf.get("q_learning_factor", 0.1)
        self.q_discount_factor = conf.get("q_discount_factor", 0.5)
        self.reward_learning_factor = conf.get("reward_learning_factor", 0.5)
        all_senosrs = conf.get("sensors", "")
        self.world_sensors = all_senosrs.get("world", "rgb0")
        self.agent_sensors = all_senosrs.get("agent", "")
        self.motors = conf.get("motors", ["left", "right", "up", "down", "eat", "drink"])

class Network:
    def __init__(self, config, sensors, motors, objectives):
        self.config = config
        self.time = 0
        self.node_count = 0
        self.nodes = {}
        self.actions = {}
        self.sensors = sensors
        self.motors = motors
        self.objectives = objectives
        self.lastChange = self.time
        self._utilityFunc = UTILITY_FUNCTIONS.get(config.utility_function)
        self._qFunc = Q_FUNCTIONS.get(config.q_function)
        self.addNodes(sensors)

    def getTime(self): return self.time
    def getNodeCount(self): return self.node_count

    def tick(self):
        self.time = self.time + 1
        self._previousSensors = self.activeSensors()
        for node in self.sensors:
            node.tick(self.time)
        if self._previousSensors != self.activeSensors():
            self.sensorsChanged = True
            self._setPreviousActive()
        self._propagate() # Tick each node, depth first
        self._findTopActive()

    def _setPreviousActive(self):
        for node in self.nodes.values():
            node.previousActive = node.pendingPreviousActive

    def _propagate(self):
        for node in self.topNodes(includeVirtual=True):
            node.tick(self.time)

    def _findTopActive(self, verbose=False):
        for node in self.nodes.values():
            node.topActive = False
        for node in self.sensors:
            node._findTopActive(verbose)

    def activeSensors(self):
        return [x for x in self.sensors if x.active]

    def allNodes(self):
        return self.nodes.values()

    def topNodes(self, includeVirtual=False):
        return [x for x in self.nodes.values() if x.isTopNode(includeVirtual)]

    def activeTopNodes(self, includeVirtual=False):
        return [x for x in self.nodes.values() if x.isTopActive(includeVirtual)]

    def virtualNodes(self):
        return [x for x in self.nodes.values() if x.isVirtual()]

    def activeVirtualNodes(self):
        return [x for x in self.virtualNodes() if x.isActive()]

    def addNodes(self, nodes):
        for node in nodes:
            self.addNode(node)

    def addNode(self, node):
        if self.hasNode(node): return False
        self.nodes[node.getName()] = node
        self.node_count = self.node_count + 1
        node.setNetwork(self)
        self.lastChange = self.time
        return True

    def deleteNode(self, node):
        # Can only delete top-nodes
        if node.permanent: return False
        if node.isTopNode() != True: return False
        for i in node.inputs:
            i.outputs.remove(node)
        del self.nodes[node.name]
        self.lastChange = self.time
        return True

    def findNode(self, name):
        return self.nodes.get(name, None)

    def hasAndNode(self, inputs):
        return self.hasNode(node.makeName("AND", inputs))

    def hasSeqNode(self, inputs):
        return self.hasNode(node.makeName("SEQ", inputs, False))

    def hasNode(self, node):
        if type(node) == str or type(node) == unicode:
            return self.findNode(node) != None
        else:
            return self.findNode(node.getName()) != None

    def createAction(self, node, motor, reward=None):
        actionId = (node.getId(), motor)
        if actionId in self.actions:
            return self.actions[actionId]
        else:
            action = Action(self, node, motor, reward)
            self.actions[actionId] = action
            return action

    def knownActions(self, objective=None):
        actions = []
        for action in self.availableActions():
            # TODO: Should this be getV? Utility? or something else?
            actions.append((action.getV(objective), action.desc()))
        return sorted(actions, key=lambda x: -x[0])

    def availableActions(self):
        return [a for a in self.actions.values() if a.isAvailable()]

    def evaluateActionUtility(self, actionQ, status):
        newQ = {objective:self._qFunc(Q, status) for objective,Q in actionQ.items()}
        print "*** EAU", actionQ, status, newQ
        return self._utilityFunc( newQ, status)

    def predictR(self, motor):
        R = { k:0.0 for k in self.objectives }
        C = 0.0
        N = 0
        for action in self.availableActions():
            if action.motor.name == motor:
                C = C + 1
                N = N + action.triggers
                for objective in self.objectives:
                    R[objective] = R[objective] + action.getR(objective)
        return {k:v/C for k,v in R.items()}, N

    def getBestAction(self, status, allowExploration=True, epsilon=None):
        actions = {motor.name:[] for motor in self.motors}
        for action in self.availableActions():
            actions[action.motor.name].append(action)

        print "ACTIONS", action

        actions_objective = {}
        for motor,v in actions.items():
            actionsQ = {}
            actions_objective[motor] = actionsQ
            for obj in self.objectives:
                actionsQ[obj] = {
                    'min': min([action.getMinQ(obj) for action in v]),
                    'max': max([action.getMaxQ(obj) for action in v]),
                    'mean': mean([action.getQ(obj) for action in v]),
                    'weighted': weightedMean([(action.getQ(obj),action.triggers) for action in v]),
                }

        print "=> OBJECTIVE_ACTIONS",;pprint(actions_objective)

        actions = []
        for action, v in actions_objective.items():
            actions.append((self.evaluateActionUtility(v, status), action, v))

        actions = sorted(actions, key=lambda x:-x[0])
        print "DECIDE", actions

        # Shouldn't really happend, unless the network is empty
        if len(actions) == 0:
            return None

        epsilon = epsilon or self.config.epsilon
        if allowExploration and random.random() < epsilon:
            bestAction = random.choice(actions)
        else:
            bestAction = actions[0]

        return bestAction

    def d(self):
        return [n.d() for k,n in sorted(self.nodes.items())]

    def printNetwork(self):
        print "NETWORK@", self.time, ":"
        for k,v in self.d():
            print
            print "NODE:", k
            pprint(v)
