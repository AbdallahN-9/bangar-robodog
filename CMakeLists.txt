cmake_minimum_required(VERSION 3.5)
project(bangar)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  config
  launch
  meshes
  textures
  urdf
  worlds
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  bangar/walk_node.py
  bangar/wheel_node.py
  bangar/turn_left_node.py
  bangar/turn_right_node.py
  bangar/sit_node.py
  bangar/camera_node.py
  bangar/bangar_controller.py
  DESTINATION lib/${PROJECT_NAME}
)

# 3. Final ament macro (Must be at the very bottom!)
ament_package()