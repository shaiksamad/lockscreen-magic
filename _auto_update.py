# !pip install auto-update

"""
shaiksamad/lockscreen-magic
v0.2.0
"""

def update():
    try:
        from auto_update import Updater
    except ModuleNotFoundError:
        import os
        os.system("pip install auto-update")

    Updater(__doc__.strip())



if __name__ == "__main__":
    update()