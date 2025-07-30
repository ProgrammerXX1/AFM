# fix_requirements.py
def update_requirements():
    lines = []
    updated = {
        "passlib": "==1.7.4",
        "bcrypt": "==3.2.2"
    }

    try:
        with open("requirements.txt", "r") as f:
            for line in f:
                pkg = line.strip().split("==")[0].lower()
                if pkg in updated:
                    lines.append(f"{pkg}{updated[pkg]}\n")
                    del updated[pkg]
                else:
                    lines.append(line)
    except FileNotFoundError:
        pass

    for pkg, version in updated.items():
        lines.append(f"{pkg}{version}\n")

    with open("requirements.txt", "w") as f:
        f.writelines(lines)

    print("✅ requirements.txt обновлён:")
    for line in lines:
        print("  ", line.strip())


if __name__ == "__main__":
    update_requirements()
