# -*- coding: utf-8 -*-
#
#    pyAnimat - Simulate Animats using Transparent Graphs as a way to AGI
#    Copyright (C) 2017  Nils Svangård
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

# TODO: Store "prediction arrows", what nodes are predicted to become active when we
# take this action. In order to build a MDP.

class Action:
    def __init__(self, network, node=None, motor=None, reward=None):
        self.network = network
        self.node = node
        self.motor = motor
        self.triggers = 0
        self.R = {k:0 for k in network.objectives}
        self.Q = {k:0 for k in network.objectives}
        self.minQ = {k:0 for k in network.objectives}
        self.maxQ = {k:0 for k in network.objectives}
        self.rewardHistory = []
        if reward: self.updateQ(reward, 0)

    def isAvailable(self):
        return self.node == None or self.node.isTopActive()

    def getName(self):
        return motor.name

    def getId(self):
        return (node.getId(), motor.name)

    def updateQ(self, reward, Qsta1):
        self.triggers = self.triggers + 1

        self.rewardHistory.append(reward)
        if len(self.rewardHistory) > self.network.config.max_reward_history:
            del self.rewardHistory[0]

        # Update expected reward
        reward_discount = self.network.config.reward_learning_factor
        for objective,r in reward.items():
            # TODO: keep track of max/min-R?
            self.R[objective] = (1-reward_discount) * self.R[objective] + reward_discount * r

        print "... Action.updateQ", self.node.name+':'+self.motor.name, reward, Qsta1
        learning = self.network.config.q_learning_factor
        gamma = self.network.config.q_discount_factor
        print "...... Pre-Q", self.Q
        for objective,r in reward.items():
            self.Q[objective] = self.Q[objective] + learning * (r + gamma*Qsta1.get(objective,0.0) - self.Q[objective])
            # TODO: assign directly if triggers == 0
            if self.triggers == 1:
                self.minQ[objective] = self.Q[objective]
                self.maxQ[objective] = self.Q[objective]
            else:
                self.minQ[objective] = min(self.minQ[objective], self.Q[objective])
                self.maxQ[objective] = max(self.maxQ[objective], self.Q[objective])
        print "...... NEW-Q", self.Q

    def getV(self, objective=None):
        return self.R.get(objective, 0.0)

    def getR(self, objective=None):
        if objective:
            return self.R.get(objective, 0.0)
        else:
            return self.R

    def getMinQ(self, objective=None):
        if objective:
            return self.minQ.get(objective, 0.0)
        else:
            return self.minQ

    def getMaxQ(self, objective=None):
        if objective:
            return self.maxQ.get(objective, 0.0)
        else:
            return self.maxQ

    def getQ(self, objective=None):
        if objective:
            return self.Q.get(objective, 0.0)
        else:
            return self.Q

    def desc(self):
        return "%s: %s %d" % (self.motor.name, str(self.R), self.triggers)

    def d(self):
        return (self.motor.name, {'Q':self.Q, 'R':self.R, 'count':self.triggers})
