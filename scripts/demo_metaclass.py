import sys


class ColorRegistrator(type):
    def __init__(cls, name, bases, namespace):
        super(ColorRegistrator, cls).__init__(name, bases, namespace)

        if not hasattr(cls, "registry"):
            cls.registry = set()

        cls.registry.add(cls)
        cls.registry -= set(bases)  # Remove base classes

    # Class property
    @property
    def count(cls):
        return len(cls.registry)

    # Metamethods, called on class objects:
    def __iter__(cls):
        return iter(cls.registry)

    def __str__(cls):
        if cls in cls.registry:
            return cls.__name__
        return cls.__name__ + ": " + ", ".join([sc.__name__ for sc in cls])


# 2. Custom root class
class Color(object, metaclass=ColorRegistrator):
    pass


# 3. Derived classes
class Blue(Color):
    pass


class Red(Color):
    pass


class Green(Color):
    pass


class Yellow(Color):
    pass


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what this
    # prints is what the reader sees on any machine.
    #
    # The guard arrived with that line. Without one the two prints below ran on
    # import, and so would the reconfigure -- which would reach into the stdout
    # of anything that imported this file. Guarding is what keeps the encoding
    # a decision this script makes about its own output.
    sys.stdout.reconfigure(encoding="utf-8")

    print(Color)
    print(Color.count)
