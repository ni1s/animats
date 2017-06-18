# -*- coding: utf-8 -*-
#
#    pyAnimat - Simulate Animats using Transparent Graphs as a way to AGI
#    Copyright (C) 2017  David Lindström
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

from node import *
from agent import ORIENTATION_MATRIX
import environment
import string
import math


class GradientSensorNode(Node):
    def __init__(self, name, sensor, environment):
        Node.__init__(self, name, permanent=True)
        self.sensor=sensor
        self.environment=environment
        if string.find(sensor, "left") != -1:
            self.type = "left"
        else:
            self.type = "right"
        self.sensor_value = 0.0
        self.old_sensor_value = 0.0

    def tick(self, time):
        if Node.tick(self, time):
            x = self.readSensor()
            if x: self.activate(time)
            else: self.deactivate(time)
            return True
        else:
            return False

    def readSensor(self):
        if self.sensor == 't': return 1
        (self.value_before_action, self.gradient_before_action) = self._value_and_gradient()
        (gradient_x, gradient_y) = self.gradient_before_action
        if gradient_x == 0.0 and gradient_y == 0.0:
            self.sensor_value_before_action = 0.0
            active = True
        else:
            bee_angle_to_gradient = self._relative_angle(gradient_x, gradient_y)
            if self.type == "left":
                active = (bee_angle_to_gradient > -22.5)
                if active: print "<< gradient ", bee_angle_to_gradient, " to the left"
            elif self.type == "right":
                active = (bee_angle_to_gradient < 22.5)
                if active: print ">> gradient ", bee_angle_to_gradient, " to the right"
        return active

    def getGradientSensorReward(self):
        (value, gradient) = self._value_and_gradient()
        return value - self.value_before_action

    def _relative_angle(self, gradient_x, gradient_y):
        (orientation_x,orientation_y) = ORIENTATION_MATRIX[self.environment.agent.orientation]
        norm = math.sqrt(orientation_x**2 + orientation_y**2)
        orientation_x *= 1/norm
        orientation_y *= 1/norm
        bee_angle = math.degrees(math.atan2(-orientation_y,orientation_x))
        gradient_angle = math.degrees(math.atan2(-gradient_y,gradient_x))
        angle_from_bee_to_gradient = gradient_angle - bee_angle
        while angle_from_bee_to_gradient > 180:
            angle_from_bee_to_gradient -= 360
        while angle_from_bee_to_gradient <= -180:
            angle_from_bee_to_gradient += 360
        return angle_from_bee_to_gradient

    # Calculate gradient in a torus world based on the 9x9 block surrounding
    def _value_and_gradient(self):
        value = 0.0
        gradient_x = 0.0
        gradient_y = 0.0
        (pos_x,pos_y) = (self.environment.agent.position[0],self.environment.agent.position[1])
        for dy in range(-4, 4):
            for dx in range(-4, 4):
                if dx != 0 or dy != 0:   # exclude the cell where the animat is located to avoid division by zero
                    x = (pos_x + dx) % self.environment.getWidth()
                    y = (pos_y + dy) % self.environment.getHeight()
                    cell = self.environment.getCell(x,y)
                    source = self.environment.config.blocks.get(cell,{}).get(self.sensor, None)
                    if cell =='f' or cell == 'p':
                        r_x = dx / 1.0
                        r_y = dy / 1.0
                        value_factor = 1.0/(r_x**2 + r_y**2)
                        gradient_factor = 1.0/(math.sqrt(r_x**2 + r_y**2)**3)
                        value += source * value_factor
                        gradient_x += source * gradient_factor * r_x
                        gradient_y += source * gradient_factor * r_y
        return (value, (gradient_x, gradient_y))

def _norm(vector):
    return math.sqrt(vector[0]**2 + vector[1]**2)