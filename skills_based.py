import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
from abc import ABC, abstractmethod
from collections import deque

class Skill(ABC):
    def __init__(self, object_name):
        self.object_name = object_name
        self.precursors = []

    @abstractmethod
    def get_value(self, *args, **kwargs):
        pass

    def add_precursor(self, precursor):
        if isinstance(precursor, Skill):
            self.precursors.append(precursor)
        else:
            raise ValueError("Precursor must be an instance of Skill")

# Skill which has a string or boolean value
class StepSkill(Skill):
    def __init__(self, object_name, value):
        super().__init__(object_name)
        if not isinstance(value, (str, bool)):
            raise ValueError("StepSkill value must be a string or boolean")
        self.value = value

    def get_value(self, *args, **kwargs):
        return self.value

# Skill which has a number or list of numbers
class NumericalSkill(Skill):
    def __init__(self, object_name, value):
        super().__init__(object_name)
        if not isinstance(value, (int, float, list)):
            raise ValueError("NumericalSkill value must be a number or list of numbers")
        if isinstance(value, list):
            if not all(isinstance(v, (int, float)) for v in value):
                raise ValueError("All elements in NumericalSkill list must be numbers")
        self.value = value

    def get_value(self, *args, **kwargs):
        return self.value

class Recognize(StepSkill):
    def __init__(self, object_name, object_type):
        super().__init__(object_name, object_type)

class Localize(NumericalSkill):
    def __init__(self, object_name, coords):
        super().__init__(object_name, coords)

class Size1D(NumericalSkill):
    def __init__(self, object_name, length):
        super().__init__(object_name, length)

class Size2D(Size1D):
    def __init__(self, object_name, width, height):
        super().__init__(object_name, [width, height])

class Angle(NumericalSkill):
    def __init__(self, object_name, angle):
        super().__init__(object_name, angle)

class RecognizeGroup(StepSkill):
    def __init__(self, object_name, condition):
        super().__init__(object_name, condition)

class Count(NumericalSkill):
    def __init__(self, object_name, count):
        super().__init__(object_name, count)

class Object:
    def __init__(self, name, component_parts, dim=2):
        self.skills = {}
        self.name = name
        self.component_parts = component_parts

        recognize = Recognize(name, name)
        self.add_skill(recognize)
        for part in component_parts:
            recognize_comp_group = part.skills.get("RecognizeGroup")
            self.add_precursor_skill(recognize, recognize_comp_group)

        localize = Localize(name, [0, 0])  # Default position
        self.add_skill(localize)
        self.add_precursor_skill(localize, recognize)

        angle = Angle(name, 0)  # Default angle
        self.add_skill(angle)
        self.add_precursor_skill(angle, localize)

        if dim == 1:
            size = Size1D(name, 0)  # Default size
        else:
            size = Size2D(name, 0, 0)  # Default size
        self.add_skill(size)
        self.add_precursor_skill(size, localize)

        recognize_group = RecognizeGroup(name, name)
        self.add_skill(recognize_group)
        self.add_precursor_skill(recognize_group, angle)
        self.add_precursor_skill(recognize_group, size)

        count = Count(name, 1)
        self.add_skill(count)
        self.add_precursor_skill(count, recognize_group)

    def add_skill(self, skill: Skill):
        self.skills[type(skill).__name__] = skill

    def get_skill_value(self, skill_name: str):
        skill = self.skills.get(skill_name)
        if skill:
            return skill.get_value()
        else:
            raise ValueError(f"Skill '{skill_name}' not found.")

    def add_precursor_skill(self, target_skill: Skill, precursor_skill: Skill):
        if target_skill:
            target_skill.add_precursor(precursor_skill)
        else:
            raise ValueError(f"Skill '{target_skill}' not found.")

    def print_skill_tree(self, skill_name):
        matplotlib.use('TkAgg')
        G = nx.DiGraph()
        start_skill = self.skills.get(skill_name)
        if not start_skill:
            raise ValueError(f"Skill '{skill_name}' not found.")

        queue = deque([start_skill])
        visited = set()

        while queue:
            current = queue.popleft()
            if not isinstance(current, Skill) or current in visited:
                continue
            visited.add(current)

            current_name = f"{type(current).__name__} ({current.object_name})"
            if not G.has_node(current_name):
                G.add_node(current_name)

            for precursor in current.precursors:
                precursor_name = f"{type(precursor).__name__} ({precursor.object_name})"
                if not G.has_node(precursor_name):
                    G.add_node(precursor_name)
                G.add_edge(precursor_name, current_name)
                queue.append(precursor)

        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='lightblue',
                node_size=2000, arrowsize=20, font_size=8, font_weight='bold')
        plt.title(f"Skill Tree for {skill_name}")
        plt.axis('off')
        plt.show()

