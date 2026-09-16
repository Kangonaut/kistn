from kistn import consts


def create_skeleton():
    # ~/.config/borgmatic.d
    consts.BORGMATIC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    consts.BORGMATIC_CONFIG_DIR.chmod(mode=0o700)
