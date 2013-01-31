#!/usr/bin/env python

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("scenefile")
args = parser.parse_args()
import subprocess, os
import trajoptpy.math_utils as mu

envfile = "/tmp/%s.xml"%os.path.basename(args.scenefile)
subprocess.check_call("python scene2xml.py %s %s"%(args.scenefile, envfile), shell=True)


import roslib
import sys
sys.path.append("/home/joschu/ros/moveit/devel/lib/python2.7/dist-packages")
sys.path.append("/home/ibrahima/moveit/devel/lib/python2.7/dist-packages")
import rospy

from moveit_msgs.msg import *
from geometry_msgs.msg import *
from shape_msgs.msg import *
from trajopt_plugin.srv import *

import actionlib

import time
import numpy as np
import json
import openravepy as rave, numpy as np


ROS_JOINT_NAMES = ['br_caster_rotation_joint', 'br_caster_l_wheel_joint', 'br_caster_r_wheel_joint', 'torso_lift_joint', 'head_pan_joint', 'head_tilt_joint', 'laser_tilt_mount_joint', 'r_shoulder_pan_joint', 'r_shoulder_lift_joint', 'r_upper_arm_roll_joint', 'r_elbow_flex_joint', 'r_forearm_roll_joint', 'r_wrist_flex_joint', 'r_wrist_roll_joint', 'r_gripper_motor_slider_joint', 'r_gripper_motor_screw_joint', 'r_gripper_l_finger_joint', 'r_gripper_l_finger_tip_joint', 'r_gripper_r_finger_joint', 'r_gripper_r_finger_tip_joint', 'r_gripper_joint', 'l_shoulder_pan_joint', 'l_shoulder_lift_joint', 'l_upper_arm_roll_joint', 'l_elbow_flex_joint', 'l_forearm_roll_joint', 'l_wrist_flex_joint', 'l_wrist_roll_joint', 'l_gripper_motor_slider_joint', 'l_gripper_motor_screw_joint', 'l_gripper_l_finger_joint', 'l_gripper_l_finger_tip_joint', 'l_gripper_r_finger_joint', 'l_gripper_r_finger_tip_joint', 'l_gripper_joint', 'torso_lift_motor_screw_joint', 'fl_caster_rotation_joint', 'fl_caster_l_wheel_joint', 'fl_caster_r_wheel_joint', 'fr_caster_rotation_joint', 'fr_caster_l_wheel_joint', 'fr_caster_r_wheel_joint', 'bl_caster_rotation_joint', 'bl_caster_l_wheel_joint', 'bl_caster_r_wheel_joint']
ROS_DEFAULT_JOINT_VALS = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.657967, 0.888673, -1.4311, -1.073419, -0.705232, -1.107079, 2.806742, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.848628, 0.7797, 1.396294, -0.828274, 0.687905, -1.518703, 0.394348, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

def has_collision(traj, manip):
    traj_up = mu.interp2d(np.linspace(0,1,100), np.linspace(0,1,len(traj)), traj)
    robot = manip.GetRobot()
    ss = rave.RobotStateSaver(robot)
    arm_inds = manip.GetArmIndices()
    env = robot.GetEnv()
    collision = False
    for (i,row) in enumerate(traj_up):
        robot.SetDOFValues(row, arm_inds)
        col_now = env.CheckCollision(robot)
        if col_now: 
            print "collision at timestep", i        
            collision = True
    return collision

def build_motion_plan_request(pos, quat, arm):
    m = MoveGroupGoal()
    m.request.group_name = "%s_arm" % arm
    target_link = "%s_wrist_roll_link" % arm[0]
    m.request.start_state.joint_state.name = ROS_JOINT_NAMES
    m.request.start_state.joint_state.position = ROS_DEFAULT_JOINT_VALS

    m.request.start_state.multi_dof_joint_state.joint_names =  ['world_joint']
    m.request.start_state.multi_dof_joint_state.frame_ids = ['odom_combined']
    m.request.start_state.multi_dof_joint_state.child_frame_ids = ['base_footprint']
    base_pose = Pose()
    base_pose.orientation.w = 1
    m.request.start_state.multi_dof_joint_state.poses = [ base_pose ]

    pc = PositionConstraint()
    pc.link_name = target_link
    pc.header.frame_id = 'odom_combined'
    pose = Pose()
    pose.position = pos

    pc.constraint_region.primitive_poses = [pose]
    
    sphere = SolidPrimitive()
    sphere.type = SolidPrimitive.SPHERE
    sphere.dimensions = [.01]
    pc.constraint_region.primitives = [ sphere ]
    
    oc = OrientationConstraint()
    oc.link_name = target_link
    oc.header.frame_id = 'odom_combined'
    oc.orientation = quat
    c = Constraints()
    c.position_constraints = [ pc ]
    c.orientation_constraints = [ oc ]
    m.request.goal_constraints = [ c ]
    
    return m

def test_grid(center_point, x_range=0.1, y_range=0.2, z_range=0.2, dx=0.05, dy=0.05, dz=0.05):
    client = actionlib.SimpleActionClient('move_group', MoveGroupAction)
    
    print "Waiting for server"
    client.wait_for_server()
    print "Connected to actionserver"

    for xp in np.arange(center_point.x - x_range, center_point.x + x_range, dx):
        for yp in np.arange(center_point.y - y_range, center_point.y + y_range, dy):
            for zp in np.arange(center_point.z - z_range, center_point.z + z_range, dz):
                p = Point()
                p.x = xp
                p.y = yp
                p.z = zp
                print "Sending planning request to point", p
                q = Quaternion() # TODO: Configure orientation
                q.w = 1
                m = build_motion_plan_request(p, q)
                client.send_goal(m)
                t1 = time.time()
                client.wait_for_result()
                t2 = time.time()
                result = client.get_result()
                print "Motion planning request took", (t2-t1), "seconds"
                
                if m.request.group_name == "right_arm": manipname = "rightarm"
                elif m.request.group_name == "left_arm": manipname = "leftarm"
                else: raise Exception("invalid group name")




                if rospy.is_shutdown(): return
    
    
def test_plan_to_pose(xyz, xyzw, leftright, robot):
    manip = robot.GetManipulator(leftright + "arm")
    client = actionlib.SimpleActionClient('move_group', MoveGroupAction)    
    print "Waiting for server"
    client.wait_for_server()
    rospy.sleep(.2)
    print "Connected to actionserver"
    p = Point(*xyz)
    q = Quaternion(*xyzw)
    m = build_motion_plan_request(p, q, leftright)
    #print "request", m
    client.send_goal(m)
    t1 = time.time()
    client.wait_for_result()
    t2 = time.time()
    result = client.get_result()
    if result is not None:
    #print "result", result
        traj = [list(jtp.positions) for jtp in result.planned_trajectory.joint_trajectory.points]
        hascol = has_collision(traj, manip)
    else:
        print "FAIL"


def update_rave_from_ros(robot, ros_values):
    rave_values = [ros_values[i_ros] for i_ros in GOOD_ROS_INDS]
    robot.SetJointValues(rave_values[:20],RAVE_INDS[:20])
    robot.SetJointValues(rave_values[20:],RAVE_INDS[20:])   

    
if __name__ == "__main__":        
    if rospy.get_name() == "/unnamed":
        rospy.init_node("foobar")
    env = rave.Environment()
    env.Load("robots/pr2-beta-static.zae")
    loadsuccess = env.Load(envfile)
    assert loadsuccess
    robot = env.GetRobots()[0]
    inds_ros2rave = np.array([robot.GetJointIndex(name) for name in ROS_JOINT_NAMES])
    GOOD_ROS_INDS = np.flatnonzero(inds_ros2rave != -1) # ros joints inds with matching rave joint
    RAVE_INDS = inds_ros2rave[GOOD_ROS_INDS] # openrave indices corresponding to those joints
    update_rave_from_ros(robot, ROS_DEFAULT_JOINT_VALS)
    

    xs, ys, zs = np.mgrid[.35:.65:.05, 0:.5:.05, .8:.9:.1]
    for (x,y,z) in zip(xs.flat, ys.flat, zs.flat):
        test_plan_to_pose([x,y,z], [0,0,0,1], "left", robot)
        raw_input()