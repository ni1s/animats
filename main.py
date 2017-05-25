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

from animat.environment import *
from animat.nodes import *
import animat.agent
import json
from pprint import pprint

# Set this to a higher number to repeat the experiment and average wellbeeing
N_REPEATS = 1

if __name__ == "__main__":
#    conf = json.load(file("examples/example-1-copepod.json"))
    conf = json.load(file("examples/example-2-sheep.json"))
#    conf = json.load(file("examples/example-3-swamp.json"))
#    conf = json.load(file("examples/example-4-seq.json"))

    config = EnvironmentConfig(conf)
    print conf

    wellbeeings = []

    for episode in range(N_REPEATS):
        env = VirtualEnvironment(config)
        agent = env.createAgent(config.agent)

        for i in range(config.maxIterations):
            env.tick()
            if agent.wellbeeing() <= 0.0:
                print "DEAD!"
                break

        # Only for the first episode, dump the network, trail and surprise matrices.
        if episode == 0:
            agent.network.printNetwork()
            env.printWorld()
            for i,x in enumerate(agent.trail):
                print i, x[0], x[1]
            print "SURPRISE MATRIX"
            pprint(agent.surpriseMatrix)
            print "SEQ SURPRISE MATRIX"
            pprint(agent.surpriseMatrix_SEQ)

        wellbeeings.append(agent.wellbeeingTrail)

    # Save the wellbeeing trails to file
    fp = open( os.path.join(config.outputPath, "wellbeeing.csv"), "w")
    print >> fp, "\n".join([";".join([str(x).replace(".",",") for x in line]) for line in zip(*wellbeeings)])
    fp.close()
