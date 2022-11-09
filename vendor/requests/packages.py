# coding: utf-8
import sys
try:
    import chardet
except ImportError:
    import warnings
    import charset_normalizer as chardet
    warnings.filterwarnings('ignore', 'Trying to detect', module='charset_normalizer')
for package in ('urllib3', 'idna'):
    locals()[package] = __import__(package)
    for mod in list(sys.modules):
        if mod == package or mod.startswith(f'{package}.'):
            sys.modules[f'requests.packages.{mod}'] = sys.modules[mod]
target = chardet.__name__
for mod in list(sys.modules):
    if mod == target or mod.startswith(f'{target}.'):
        target = target.replace(target, 'chardet')
        sys.modules[f'requests.packages.{target}'] = sys.modules[mod]
