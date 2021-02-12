from django import template
register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def pretty_print_bytes(bytes):
    for unit in ['B', 'K', 'M', 'G']:
        if bytes < 1024.0:
            return "{}{}".format(round(bytes, 2), unit)
        bytes /= 1024.0
    return "{}{}".format(round(bytes, 2), "T")


@register.filter
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()
