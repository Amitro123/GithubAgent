import os
import shutil
import time

def cleanup_folder(folder, patterns=None, days_old=None):
    now = time.time()
    removed = []
    if not os.path.exists(folder):
        return removed
    for fname in os.listdir(folder):
        fpath = os.path.join(folder, fname)
        remove = True
        if patterns and not any(fname.endswith(pat) for pat in patterns):
            remove = False
        if days_old is not None:
            age = (now - os.path.getmtime(fpath)) / 86400
            if age < days_old:
                remove = False
        if remove:
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                removed.append(fpath)
            except Exception as e:
                print(f"Failed cleaning {fpath}: {e}")
    return removed
