import numpy as np
import xml.etree.ElementTree as ET
import os, random

DIR_FILE = os.path.dirname(__file__)

class Agent():
    def __init__(self, name, Dt=0.1, pos = np.array([0.0,0.0,0.0]), psi0 = 0.0, agent_xml="default.xml"):
        '''Agent Object: parameters
        name: str, unique name 
        Dt: time subdivision
        pos: list or numpy array of 3 elements, determining global position at start, default is 0,0,0
        psi0: float: initial heading in degrees, default is 0.0 (North)
        agent_xml: filename of agent setting, default is default.xml'''
        # private
        self._cmd_force = np.array([0.0,0.0])
        self._cmd_local_vel = np.array([0.0,0.0])
        # Fixed time division
        self.Dt = Dt
        # Set inital condition
        self.name = name
        # Set initial positiion
        if not 3==len(pos): raise ValueError ('Passed initial position is not a 3 element Array or list')
        if type(pos) in (tuple,list): self.pos =np.array(pos).astype(float) #convert to numpy array
        else: self.pos = pos.astype(float)
        # Set initial heading
        self.psi = psi0
        # genrate random seed based on name
        self.rnd = np.random.RandomState(hash(name)%2**30)
        # Load agent parameters from xml
        self.parse_agent_parameters(agent_xml)
        # Parameter initialization
        self.internal_clock= 0.0
        self.incurrent_velocity = np.array([0,0])
        # Sensors initialization
        self.measured_depth = pos[2]
        self.measured_heading = psi0
        self.measured_pos = pos[0:2]
        # Command initialization
        self.cmd_depth = pos[2]
        self.cmd_heave = 0
        self.cmd_heading = psi0
        self.cmd_yawrate = 0
        self.cmd_planar = np.array(pos[0:2])
        self.cmd_local_vel = np.array([0,0])
        self.cmd_forces = np.array([0,0])
        # step memory for collisions
        self.last_step_planar = [np.array(pos[0:2]),np.array([0,0])]
        self.other_forces = np.array([0,0])

    @property
    def cmd_forces(self):
        return self._cmd_force
    @cmd_forces.setter
    def cmd_forces(self,input):
        ''' Set force command:
            accepts: numpy array, list , tuple, float
            if the input is float, assume sway to be 0.0'''
        if   type(input)==np.ndarray and 2==np.size(input):
            self._cmd_force =  np.squeeze(input.astype('float'))
        elif type(input) in (list,tuple) and 2==len(input):
            self._cmd_force =  np.array(input).astype('float')
        elif type(input)==int or type(input)==float:
            self._cmd_force =  np.array([float(input),0.0])
        else: raise ValueError('force command must be length 2 numpy array, 2 element list, tuple or a number.')

    @property
    def cmd_local_vel(self):
        return self._cmd_local_vel
    @cmd_local_vel.setter
    def cmd_local_vel(self,input):
        # sanity checks
        if   type(input)==np.ndarray and 2==np.size(input):
            self._cmd_local_vel =  np.squeeze(input.astype('float'))
        elif type(input)==list and 2==len(list):
            self._cmd_local_vel =  np.array(input).astype('float')
        elif type(input)==int or type(input)==float:
            self._cmd_local_vel =  np.array([float(input),0.0])
        else: raise ValueError('force command must be length 2 numpy array, 2 element list or a number.')


    def parse_agent_parameters(self, local_path):
        ''' Read the xml file for the agents charateristics'''
        def parse_matrix(element):
        # Split the text into rows and then convert each row to a list of floats
            matrix = np.array([list(map(float, row.split())) for row in element.text.strip().split('\n')])
            return np.squeeze(matrix)
        # fix path if local or global
        if os.path.isabs(local_path): path = local_path
        else: path = os.path.join(DIR_FILE,local_path)
        tree = ET.parse(path)
        root = tree.getroot()
        sim_agent = root.find('sim_agent')
        if sim_agent is None: raise ValueError("The XML does not contain a <sim_agent> element.")
        # Parse required parameters
        self.mass = float(sim_agent.find('mass').text)
        self.added_mass = parse_matrix(sim_agent.find('added_mass'))
        self.tot_mass = self.added_mass + np.array([[self.mass,0],[0,self.mass]])
        self.quadratic_damping = parse_matrix(sim_agent.find('quadratic_damping'))
        # Parse optional parameters
        self.linear_damping = parse_matrix(sim_agent.find('linear_damping')) if sim_agent.find('linear_damping') is not None else np.zeros([2,2])
        # Parse Control depth
        self.depth_control = sim_agent.find('depth_control').text
        if "step"        ==self.depth_control: self.step_depth = float(sim_agent.find('step_depth').text)
        if "proportional"==self.depth_control: 
            self.proportional_depth = float(sim_agent.find('proportional_depth').text)
            self.heave_limit        = float(sim_agent.find('heave_limit').text)
        # Parse Control heading
        self.heading_control = sim_agent.find('heading_control').text
        if "step"        ==self.heading_control: self.step_heading = float(sim_agent.find('step_heading').text)
        if "proportional"==self.heading_control: 
            self.proportional_heading = float(sim_agent.find('proportional_heading').text)  
            self.yawrate_limit        = float(sim_agent.find('yawrate_limit').text) 
        # Parse Control planar
        self.planar_control = sim_agent.find('planar_control').text
        if "step"==self.planar_control: self.step_planar= float(sim_agent.find('step_planar').text)
        #Parse Navigation errors
        self.e_depth     = parse_matrix(sim_agent.find('e_depth'))     if sim_agent.find('e_depth')     is not None else np.zeros(2)
        self.e_heave     = parse_matrix(sim_agent.find('e_heave'))     if sim_agent.find('e_heave')     is not None else np.zeros(2)
        self.e_heading   = parse_matrix(sim_agent.find('e_heading'))   if sim_agent.find('e_heading')   is not None else np.zeros(2)
        self.e_yawrate   = parse_matrix(sim_agent.find('e_yawrate'))   if sim_agent.find('e_yawrate')   is not None else np.zeros(2)
        self.e_position  = parse_matrix(sim_agent.find('e_position'))  if sim_agent.find('e_position')  is not None else np.zeros(2)
        self.e_local_vel = parse_matrix(sim_agent.find('e_local_vel')) if sim_agent.find('e_local_vel') is not None else np.zeros(2)        
        self.clock_drift = float(sim_agent.find('clock_drift').text) if sim_agent.find('clock_drift') is not None else 0
        ## TODO consider adding randomization

        # Parse Sensors
        sensors_root = root.find('sensors')
        self.sensors={}
        if not (sensors_root is None):      #skip if not defined
        # NN Detector
            detector_root = sensors_root.find('NNDetector')
            if detector_root:
                self.sensors['NNDetector']={'period': float(detector_root.find('period').text)}
                self.sensors['NNDetector']['field_of_view']= parse_matrix(detector_root.find('field_of_view'))
                self.sensors['NNDetector']['visibility_model'] = detector_root.find('visibility_model').text
                if "linear"== self.sensors['NNDetector']['visibility_model']:
                    self.sensors['NNDetector']['points'] = parse_matrix(detector_root.find('points'))
                #Parse Sensor errors
                self.sensors['e_NND_distance'] = parse_matrix(detector_root.find('e_distance')) if detector_root.find('e_distance') is not None else np.zeros(2)
                self.sensors['e_NND_alpha'] =    parse_matrix(detector_root.find('e_alpha'))    if detector_root.find('e_alpha')    is not None else np.zeros(2)
                self.sensors['e_NND_beta'] =    parse_matrix(detector_root.find('e_beta'))      if detector_root.find('e_beta')     is not None else np.zeros(2)
                # add detector element
                self.NNDetector={'time_lapsed': self.rnd.uniform(0,self.sensors['NNDetector']['period'])}
            acoustic_root = sensors_root.find('Acoustic_Ranging')
            if acoustic_root:
                self.sensors['ac_msg_length'] = float(acoustic_root.find('msg_length').text)
                self.sensors['e_ac_range'] = parse_matrix(acoustic_root.find('e_ac_range')) if acoustic_root.find('e_ac_range') is not None else np.zeros(2)
                self.sensors['e_ac_doppler']  = parse_matrix(acoustic_root.find('e_doppler'))  if acoustic_root.find('e_doppler')  is not None else np.zeros(2)

        # parse collisions
        collision_root = root.find('collisions')
        self.collision = {}
        if not (collision_root is None): #skip if not defined
            self.collision['radius'] = float(collision_root.find('radius').text)
            self.collision['height'] = float(collision_root.find('height').text)


    def emulate_error (self, data, error):
        ''' Alter the input data to simulate measurment errors '''
        data += error[0]
        data += self.rnd.normal(scale=error[1])
        return data

    def tick(self):
        ''' Update the Agent tick'''
        self.update_internal_clock()
        self.update_sensors()
        self.update_heading()
        self.update_depth()
        self.update_planar(self.Dt)
        
    def update_internal_clock(self):
        ''' Keep track of the internal time clock'''
        self.internal_clock += self.Dt*(1+self.clock_drift*1e-6)

    def update_sensors(self):
        ''' Update value of control feedback sensor'''
        self.measured_depth = self.emulate_error(self.pos[2],self.e_depth)
        self.measured_heading = (self.emulate_error(self.psi,self.e_heading)) %360
        self.measured_pos = np.array([
            self.emulate_error(self.pos[0],self.e_position),
            self.emulate_error(self.pos[1],self.e_position) ])

    def update_depth(self):
        ''' Update Agent depth, based on selected behavior '''
        correction = self.cmd_depth - self.measured_depth
        if   "ideal"==self.depth_control:
            self.pos[2] += correction
        elif "step"==self.depth_control:
            step = self.Dt*self.step_depth
            if abs(correction)< step: self.pos[2] += correction
            else: 
                self.pos[2] = self.pos[2] + step * np.sign(correction)
        elif "proportional"==self.depth_control:
            w = self.proportional_depth* correction
            if w> self.heave_limit: w = self.heave_limit
            if w<-self.heave_limit: w =-self.heave_limit
            self.pos[2] += self.emulate_error(w,self.e_heave)*self.Dt
        elif "heave"==self.depth_control:
            self.pos[2] += self.emulate_error(self.cmd_heave,self.e_heave)*self.Dt

    def update_heading(self):
        ''' Update Agent heading, based on selected behavior '''
        correction = (self.cmd_heading - self.measured_heading)%360
        if correction>180: correction -=360
        if "ideal"==self.heading_control:
            self.psi += correction
        elif "step"==self.heading_control:
            step = (self.Dt*self.step_heading)
            if abs(correction)<step: self.psi += correction
            else: self.psi += step * np.sign(correction)
        elif "proportional"==self.heading_control:
            r = self.proportional_heading* correction
            if r> self.yawrate_limit: r = self.yawrate_limit
            if r<-self.yawrate_limit: r =-self.yawrate_limit
            self.psi += self.emulate_error(r,self.e_yawrate)*self.Dt
        elif "yawrate"==self.heading_control:
            self.psi += self.emulate_error(self.cmd_yawrate,self.e_yawrate)*self.Dt
        # return result in the [0,360) range
        self.psi %=360

    def update_planar(self, Dt):
        ''' tick based update of the planar position'''
        ## Save last step state
        self.last_step_planar = [self.pos[0:2],self.incurrent_velocity]
        ## calculate correction and angles
        x_correction = self.cmd_planar[0]-self.measured_pos[0]
        y_correction = self.cmd_planar[1]-self.measured_pos[1]
        sinpsi = np.sin(np.deg2rad(self.psi))
        cospsi = np.cos(np.deg2rad(self.psi)) 

        if "ideal"==self.planar_control:
            self.pos[0] += x_correction
            self.pos[1] += y_correction
        elif "step"==self.planar_control:
            step = (self.Dt*self.step_planar)
            d_correction = np.linalg.norm([x_correction,y_correction])
            if abs(d_correction)<step: 
                self.pos[0] += x_correction
                self.pos[1] += y_correction
            else:
                self.pos[0] += step*x_correction/d_correction
                self.pos[1] += step*y_correction/d_correction
        elif "local_velocity"==self.planar_control:
            # NED convention
            effective_velocities = [self.emulate_error( self.cmd_local_vel[0],self.e_local_vel),
                                    self.emulate_error(-self.cmd_local_vel[1],self.e_local_vel)]
            self.pos[0] += (effective_velocities[0] * cospsi + effective_velocities[1] * sinpsi) * Dt
            self.pos[1] += (effective_velocities[0] * sinpsi - effective_velocities[1] * cospsi) * Dt
        ## Case local force is the only one compatible to force collisions
        elif "local_forces"==self.planar_control:
            # Ned compatibility
            external_forces = np.array([ self.cmd_forces[0]+self.other_forces[0],
                                        -self.cmd_forces[1]-self.other_forces[1]])
            F_tot = (external_forces +
                     np.matmul(self.linear_damping, self.incurrent_velocity)+
                     np.matmul(self.quadratic_damping,abs(self.incurrent_velocity)*self.incurrent_velocity)
                     )
            acc_local = np.matmul(np.linalg.inv(self.tot_mass),F_tot)
            self.incurrent_velocity = self.incurrent_velocity + acc_local * Dt
            Dx = (self.incurrent_velocity[0] * cospsi + self.incurrent_velocity[1] * sinpsi) * Dt
            Dy = (self.incurrent_velocity[0] * sinpsi - self.incurrent_velocity[1] * cospsi) * Dt
            self.pos[0] += Dx
            self.pos[1] += Dy

    def cmd_fhd(self,force,heading,depth):
        ''' typical triplet of commands, Force control- depth and heading step'''
        self.cmd_forces = force
        self.cmd_heading = heading
        self.cmd_depth = depth

    def cmd_xyz_phi (self, position, heading=None):
        ''' position command, step '''
        self.cmd_planar = position[0:2]
        if 3==len(position): self.cmd_depth = position[3]
        if heading: self.cmd_heading = heading

if __name__ == '__main__':
    A1 = Agent("A1",0.1)
    A1.cmd_forces = np.array([1,0])
    A1.cmd_depth = 0.0
    A1.cmd_heading = 0
    for i in range(30):
        A1.tick()
        # if i%10==0: print(f'{A1.pos[0]:.6f}, {A1.psi:.6f}')
