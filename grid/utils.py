from grid.models.level import Level
import hashlib

# Default Group 2 - Entrepreneurs


def calculate_viral_level(levels, group=2):
    current_level = Level.objects.filter(
        group=group).order_by('value').last()
    for viralLevel in levels:
        category = viralLevel.get('category')
        level = viralLevel.get('level')
        if level is None:
            return Level.objects.filter(
                group=group).order_by('value').first()
        elif level.value < current_level.value:
            current_level = level
    return current_level


def generate_hash(time):
    """Generate a 40 character long hash"""
    new_hash = hashlib.sha1()
    new_hash.update(str(time).encode('utf-8'))
    return new_hash.hexdigest()
