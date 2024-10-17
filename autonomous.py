from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3, Point3, Filename, getModelPath, PNMImage, Texture
from direct.task import Task
from math import sin, cos, radians

class AutonomousCar(ShowBase):
    def __init__(self):
        super().__init__()

        # Add the directory where your models are located
        getModelPath().appendPath(Filename.fromOsSpecific("E:/3d/models"))

        # Load the environment and models
        self.setup_environment()
        self.setup_car_model()
        self.setup_camera()

        # Load the texture for the map to sample pixel colors
        self.map_texture = None  # For holding the texture image
        self.load_map_texture()

        # Car movement parameters
        self.speed = 0
        self.steering_angle = 0
        self.max_forward_speed = 20
        self.max_reverse_speed = -10
        self.acceleration_rate = 0.2
        self.manual_mode = True  # Start in manual mode
        self.autonomous_speed = 10  # Speed for autonomous mode

        # Steering correction in autonomous mode
        self.autonomous_steering_correction = 0

        # Setup key controls
        self.setup_controls()

        # Task to update the car's position
        self.taskMgr.add(self.update_car, "UpdateCarTask")

    def setup_environment(self):
        """Load the environment model."""
        self.map = self.loader.loadModel("plane.egg")
        self.map.reparentTo(self.render)
        self.map.setScale(1, 1, 1)  # Adjust scaling if needed
        self.map.setPos(0, 0, 0)  # Center the map

    def load_map_texture(self):
        """Load the map's texture and convert it to a PNMImage for sampling."""
        map_texture = self.map.findTexture('*')
        if map_texture:
            self.map_texture = PNMImage()
            map_texture.store(self.map_texture)  # Convert the texture to a PNMImage

    def setup_car_model(self):
        """Load and position the car on the starting green grid."""
        self.car = self.loader.loadModel("SPARC_.egg")  
        self.car.reparentTo(self.render)
        self.car.setScale(0.1, 0.1, 0.1)  # Adjust size
        self.car.setPos(-3, 8, 0.05)  # Adjust to match the green grid position
        self.car.setH(90)  # Ensure the car faces the correct direction (toward the track)

    def setup_camera(self):
        """Position the camera for a top-down view."""
        self.camera.setPos(0, -40, 20)  
        self.camera.lookAt(self.car)  
        self.camera.setP(-90)  # Top-down pitch

    def setup_controls(self):
        """Configure key controls."""
        self.accept("w", self.accelerate, [1])
        self.accept("s", self.accelerate, [-1])
        self.accept("a", self.steer, [-1])
        self.accept("d", self.steer, [1])
        self.accept("w-up", self.stop_accelerate)
        self.accept("s-up", self.stop_accelerate)
        self.accept("a-up", self.stop_turn)
        self.accept("d-up", self.stop_turn)
        self.accept("m", self.toggle_mode)

    def accelerate(self, increment):
        """Update the car's speed."""
        if self.manual_mode:
            self.speed += increment * self.acceleration_rate
            self.speed = max(self.max_reverse_speed, min(self.speed, self.max_forward_speed))

    def stop_accelerate(self):
        """Stop the car."""
        self.speed = 0

    def steer(self, direction):
        """Steer the car."""
        if self.manual_mode and self.speed != 0:
            self.steering_angle = direction * 15

    def stop_turn(self):
        """Reset steering."""
        self.steering_angle = 0

    def toggle_mode(self):
        """Switch between manual and autonomous mode."""
        self.manual_mode = not self.manual_mode
        print(f"Switched to {'Manual' if self.manual_mode else 'Autonomous'} Mode")
        if not self.manual_mode:
            self.speed = 0
            self.steering_angle = 0
            self.autonomous_steering_correction = 0  # Reset correction

    def update_car(self, task):
        """Update the car's position and orientation."""
        dt = globalClock.getDt()

        if self.manual_mode:
            heading = self.car.getH() + (self.steering_angle * dt)
            self.car.setH(heading)
            dx = -sin(radians(heading)) * self.speed * dt
            dy = cos(radians(heading)) * self.speed * dt
            self.car.setPos(self.car.getX() + dx, self.car.getY() + dy, self.car.getZ())
        else:
            self.run_autonomous_logic(dt)

        # Check if the car is on the track
        if not self.is_car_on_track():
            print("Car off the track! Correcting.")
            self.autonomous_steering_correction = 1 if self.car.getX() < 0 else -1

        # Ensure car stays within map boundaries
        self.check_boundaries()

        # Keep the camera centered on the car
        self.camera.setPos(self.car.getX(), self.car.getY() - 40, 20)
        self.camera.lookAt(self.car)

        return Task.cont

    def run_autonomous_logic(self, dt):
        """Make the car follow the track autonomously."""
        heading = self.car.getH() + self.autonomous_steering_correction
        self.car.setH(heading)

        dx = -sin(radians(heading)) * self.autonomous_speed * dt
        dy = cos(radians(heading)) * self.autonomous_speed * dt

        self.car.setPos(self.car.getX() + dx, self.car.getY() + dy, self.car.getZ())

    def is_car_on_track(self):
        """Check if the car is on the black track using texture sampling."""
        if not self.map_texture:
            return True  # If no texture, assume it's on the track

        # Get the car's current 3D position and convert to 2D coordinates (map space)
        car_pos = self.car.getPos()
        car_x, car_y = car_pos.getX(), car_pos.getY()

        # Convert 3D world coordinates to texture coordinates (adjusted)
        u = int((car_x + 10) * (self.map_texture.getXSize() / 20))  # Adjust based on track dimensions
        v = int((car_y + 10) * (self.map_texture.getYSize() / 20))

        # Get the pixel color from the texture at the car's position
        if 0 <= u < self.map_texture.getXSize() and 0 <= v < self.map_texture.getYSize():
            r, g, b = self.map_texture.getRed(u, v), self.map_texture.getGreen(u, v), self.map_texture.getBlue(u, v)
            # Check if the pixel is black (or close to black)
            return (r < 10 and g < 10 and b < 10)
        return False

    def check_boundaries(self):
        """Keep the car within the map boundaries."""
        car_pos = self.car.getPos()
        if car_pos.getX() < -50: self.car.setX(-50)
        if car_pos.getX() > 50: self.car.setX(50)
        if car_pos.getY() < -50: self.car.setY(-50)
        if car_pos.getY() > 50: self.car.setY(50)

app = AutonomousCar()
app.run()
