# Make sure to have the add-on "Connectivity/ZMQ remote API server"
# running in CoppeliaSim
#
# Following are required and should be installed:
# pip install pyzmq
# pip install cbor
from multiprocessing import Process

# from turtle import distance
from logging import NullHandler
# from turtle import delay
from jmetal.algorithm.singleobjective.genetic_algorithm import GeneticAlgorithm
from jmetal.algorithm.singleobjective.evolution_strategy import EvolutionStrategy
from jmetal.operator import BinaryTournamentSelection, PolynomialMutation, SBXCrossover
from jmetal.util.termination_criterion import StoppingByEvaluations
from jmetal.lab.visualization import Plot

from jmetal.problem import Sphere
from jmetal.core.problem import FloatProblem
from jmetal.core.solution import FloatSolution
from imageai.Detection import VideoObjectDetection, ObjectDetection


from doctest import OutputChecker
from matplotlib import image
from zmqRemoteApi import RemoteAPIClient
from PIL import Image

import csv
import numpy
import os.path
import os
import cv2
import time
import math, random
import numpy as np

summer = 0 #sum all failures
dist_function_checker= [] #to hold boolean values for when event condition is satified or not.
config_space_holder = [] #list of list containing all rgb values during when event condition is satisfied or not 

print('Program started')

client = RemoteAPIClient()
# client.setsynchronous(True)
client.setStepping(True)
sim = client.getObject('sim')

# print(sim.getSimulationState() != sim.simulation_paused)

defaultIdleFps = sim.getInt32Param(sim.intparam_idle_fps)
sim.setInt32Param(sim.intparam_idle_fps, 0)

# gripperHandle = sim.getObjectHandle("RG2_openCloseLoopDummyA")
simBase=sim.getObjectHandle('LBR_iiwa_7_R800')
simTip=sim.getObjectHandle('IkTip')
simTarget=sim.getObjectHandle('IkTarget')
humanHandle = sim.getObjectHandle("Bill")
visionSensorHandle = sim.getObjectHandle("Vision_sensor") #client to get sensor handle
# cameraStream = sim.getObjectHandle("DefaultCamera")
# human_hand_left = sim.getObjectHandle("IkTip_leftHand") #client to get left hand tip handle
human_hand_right = sim.getObjectHandle("IkTip_rightHand") #client to get left hand tip handle
lightHandleA = sim.getObjectHandle("DefaultLightA")
lightHandleB = sim.getObjectHandle("DefaultLightB")
lightHandleC = sim.getObjectHandle("DefaultLightC")
lightHandleD = sim.getObjectHandle("DefaultLightD")


execution_path = "/home/jubril/Downloads"

class Simulation(FloatProblem):
    
    def __init__(self, lower_bound, upper_bound):
        super().__init__()
        
        # initial parameters
        self.number_of_variables = 7 # decision variables
        self.number_of_objectives = 1
        self.number_of_constraints = 0
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        
        self.obj_directions = [self.MINIMIZE] # the objective should be maximized
        # self.obj_labels = ['f(x1, x2)'] # objectives' name


    def emergency_stop(self):
        print ("Emergency situation detected")
        sim.stopSimulation()

    
    def evaluate(self, solution: FloatSolution) -> FloatSolution:
    
        # try:

        difA1 = round(solution.variables[0],2)
        difA2 = round(solution.variables[1],2)
        difA3 = round(solution.variables[2],2)

        #time to start actuating the robot
        timestep = int(solution.variables[3]) #time to start actuating the robot can only be an integer
        vel = round(solution.variables[4],2) #velocity of the robot


        timestepprime = int(solution.variables[5]) #time to start actuating the human can only be an integer

        velprime = round(solution.variables[6],2) #hand velocity of the human

        # simulation data array

        simdata = []
        startTime = time.time()

        '''# sim.scripttype_mainscript (0)
        sim.scripttype_childscript (1)
        sim.scripttype_addonscript (2)
        sim.scripttype_customizationscript (6)
        sim.scripttype_sandboxscript (8)'''
        

        stateA,x,difA,specA = sim.getLightParameters(lightHandleA)


        # stateB,_,difB,specB = sim.getLightParameters(lightHandleB)
        # # print(stateB, difB, specB)

        # #turn off lights A and B after the 3rd and 7th runs respectively

        # # if n == 3:
        # sim.setLightParameters(lightHandleA, 1 , None, [difA1, difA2, difA3], [0,0,0])
        sim.setLightParameters(lightHandleA, 1 , [0, 0, 0], [difA1, difA2, difA3], [0,0,0])

        # sim.callScriptFunction("setwaitTime@LBR_iiwa_7_R800",sim.scripttype_childscript,timestep)
        # sim.callScriptFunction("setwaitTime@Bill",sim.scripttype_childscript,timestepprime)
        
        sim.setInt32Signal("waitTimeBill", timestepprime)
        sim.setInt32Signal("waitTimeRobot", timestep)
        sim.setFloatSignal("velBill", velprime)
        sim.setFloatSignal("velRobot", vel)
        sim.startSimulation()
        time.sleep(2)


        # time.sleep(2)
        # sim.callScriptFunction("setParameters@Bill",sim.scripttype_childscript,timestepprime, velprime)   
        # sim.callScriptFunction("setParameters@LBR_iiwa_7_R800",sim.scripttype_childscript,timestep, vel)


        # p1 = Process(target=sim.callScriptFunction("setwaitTime@LBR_iiwa_7_R800",sim.scripttype_childscript,timestep))
        # p1.start()
        # p2 = Process(target= sim.callScriptFunction("setwaitTime@Bill",sim.scripttype_childscript,timestepprime) )
        # p2.start()
        # p1.join()
        # p2.join()

        dist = np.Inf

     
        
        # print(sim.callScriptFunction("getVelocity@LBR_iiwa_7_R800",sim.scripttype_childscript,))


        while sim.getSimulationState() != sim.simulation_stopped:
        # while sim.getSimulationTime() < 60:
        # while (dist > 0.0001) and (sim.getSimulationTime() < 7): #time

        #get vision sensor capture. Default way provided by CoppeliaSim
            # img, resX, resY = sim.getVisionSensorCharImage(visionSensorHandle)
            

            img, resX, resY = sim.getVisionSensorCharImage(visionSensorHandle)

            #==========================================================================================================================
            '''This part is for processing Vision sensor images. Vision sensors currently not working as expected'''
            #convert np array buffer to an image

            img = np.frombuffer(img, dtype=np.uint8).reshape(resX, resY, 3)
            # img = sim.transformbuffer(img, sim.buffer_uint8rgb, 1, 0, sim.buffer_uint8)

            #convert from BGR to RBG
            img = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0)
            
            # sim.saveImage(img, [resX, resY] ,0, "/home/jubril/Downloads/CoppeliaSim/programming/zmqRemoteApi/clients/python/RACAIS/test.jpg", 100)
            
        

            
            # img = img.convert()
            # print(sim.getRealTimeSimulation())
            # img.save("image.jpg")
            # print(sim.getRealTimeSimulation())
            # img = np.frombuffer(img, dtype=np.uint8).reshape(resX, resY, 3)

            # detector = ObjectDetection()
            # # detector.setModelTypeAsRetinaNet()
            # detector.setModelTypeAsYOLOv3()
            # # detector.setModelPath( os.path.join(execution_path , "resnet50_coco_best_v2.1.0.h5"))
            # detector.setModelPath( os.path.join(execution_path , "yolo.h5"))
            # detector.loadModel()
            # # detections = detector.detectObjectsFromImage(input_image=os.path.join(execution_path , "image.jpg"), output_image_path=os.path.join(execution_path , "imagenew.jpg"))
            # # detections = detector.detectObjectsFromImage(input_image=img, output_image_path='')
            # returned_image, detections, extracted_objects = detector.detectObjectsFromImage(input_image="image.jpg", output_type="array", extract_detected_objects=True, minimum_percentage_probability=30)

            # print(sim.getRealTimeSimulation())
            '''In CoppeliaSim images are left to right (x-axis), and bottom to top (y-axis)
            (consistent with the axes of vision sensors, pointing Z outwards, Y up)
            and color format is RGB triplets, whereas OpenCV uses BGR:'''
            
            # cv2.imshow('Detected', img)
            # # img = Image.fromarray(img, 'RGB')
            # # img.save("image.jpg")
            # cv2.waitKey(3)
            # client.step()
            # if os.path.exists("image.jpg"):

            # camera = cv2.VideoCapture(visionSensorHandle)
            # detector = VideoObjectDetection()
            # detector.setModelTypeAsYOLOv3()
            # detector.setModelPath(os.path.join(execution_path , "yolo.h5"))
            # detector.loadModel()

            # video_path = detector.detectObjectsFromVideo(input_file_path=os.path.join( execution_path, "traffic-mini.mp4"),
            #                         output_file_path=os.path.join(execution_path, "traffic_mini_detected_1")
            #                         , frames_per_second=29, log_progress=True)

            # video_path = detector.detectObjectsFromVideo(camera_input=camera,
            #                                 output_file_path=os.path.join(execution_path, "camera_detected_1")
            #                                 , frames_per_second=29, log_progress=True)
            
            # print(video_path)
            
            # print(type(returned_image))
            # # cv2.imshow('Detected', returned_image)
            # img = cv2.imread("image.jpg")

            # cv2.imshow("read", img)
            # cv2.waitKey(3)
            # client.step()

            # img = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0)
            # img = np.array(img)
   
            # lower = np.array([0, 51, 0])
            # 126, 116, 104
            
            
            lower = np.array([100, 100, 90])   
            upper = np.array([188, 170, 147])

            # upper = np.array([151, 255, 151])
            mask = cv2.inRange(img, lower, upper)
            # # print(max(mask))
            # print(mask)

            result, distance_left, objectPair = sim.checkDistance(simTip, human_hand_right, 0)

            #determine if the robot is moving at time of collision (or when evaluation happens)
            #if robot is moving give ctual value, if not, return large value
            #create check velocity functuion in child script and call here
            #make hazards less if experiment returns large hazard size
            jointspeedRobot = sim.getFloatSignal("jointvelRobot")
            if jointspeedRobot is None:
                jointspeedRobot = 0
            # print(jointspeedRobot)
            

            if cv2.countNonZero(mask) > 0:
            #
                Simulation.emergency_stop(self)
                # return solution
            
            else:
        
                output = cv2.bitwise_and(img, img, mask = mask)

        # cv2.imshow('Detected', np.hstack((img,output)))

                # cv2.imshow('Masked', output)
                # cv2.waitKey(3)
  
            #closing all open windows 
            # cv2.destroyAllWindows() 

            # print(((sim.checkDistance(simTip, human_hand_right, 0))[2]))
            # result, distance_left, objectPair = sim.checkDistance(simTip, human_hand_right, 0)
            # print("distance is", distance_left)
            
            client.step()

            _, distance_left, _ = sim.checkDistance(simTip, human_hand_right, 0)

            # print("distance between actors is", distance_left[6])
            if (distance_left[6] < dist):
                dist = distance_left[6]
            
            
            # if dist < 1.1:
            #     print(solution.variables)

            
            # time.sleep(0.1)
            
            # print(dist, sim.getSimulationTime()
        if (dist < 0.05) and (jointspeedRobot <= 0):
            with open("result_ES.txt", 'a') as output:
                output.write("False_fail: ")
                output.write(str(solution.variables).strip("[]"))
                output.write('\n')

        elif (dist < 0.05) and (jointspeedRobot > 0):
            with open("result_ES.txt", 'a') as output:
                output.write("Fail: ")
                output.write(str(solution.variables).strip("[]"))
                output.write('\n')

        else:
            with open("result_ES.txt", 'a') as output:
                output.write("Pass: ")
                output.write(str(solution.variables).strip("[]"))
                output.write('\n')

            #maximization requires multiplying by -1 since jmetal defaults to minimization
        cv2.destroyAllWindows() 


        solution.objectives[0] = dist

        
        sim.setInt32Param(sim.intparam_idle_fps, defaultIdleFps)


        print('Program ended')


        #to set default light A to on, and then it's diffuse and specular components to their defualt
        sim.setLightParameters(lightHandleA, 1 , [0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5])
        sim.stopSimulation()         
            # return solution
            # print(solution.variables)

        # first column saves the current fitness value
        simdata.append(solution.objectives[0])
        # second column stores individual simulation time
        simdata.append((time.time() - startTime))

        # simdataCollection.append(simdata)

        with open('run_details_ES.csv', 'a', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(simdata)
        # with open("run_details.txt", 'a') as runfile:
        #     runfile.write("Fitness: "+str(solution.objectives[0])+'\n')
        #     runfile.write("Simulation time: "+str(time.time() - startTime)+'\n')

        return solution
                
        # except:
            # print('Program ended')
            # sim.stopSimulation()
            # exit()
    
    def get_name(self):
        return 'Simulation problem'


def main():

    problem = Simulation([0, 0, 0, 1, 0.05, 1, 0.1], [1, 1, 1, 50, 0.5, 50, 0.5])


    algorithm = EvolutionStrategy(
        problem=problem,
        mu=20, #10 #represents population size
        lambda_=20, #10 #represents offspring population size
        elitist=True,
        mutation=PolynomialMutation(probability=1.0 / problem.number_of_variables),
        termination_criterion=StoppingByEvaluations(max_evaluations=400),
    )

    algorithm.run()
    result = algorithm.get_result()

    print("Algorithm: " + algorithm.get_name())
    print("Problem: " + problem.get_name())
    print("Solution: " + str(result.variables[0]))
    print("Fitness:  " + str(result.objectives[0]))
    print("Computing time: " + str(algorithm.total_computing_time))
    # cv2.waitKey(0) 

    #closing all open windows 
    cv2.destroyAllWindows()
    exit()

if __name__ == "__main__":
    main()


