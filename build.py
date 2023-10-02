

if __name__ == "__main__":
    import requests
    import subprocess
    import argparse
    from zipfile import ZipFile
    from pathlib import Path
    import webbrowser
    from github import Github
    import click
    import re

    def update_init_file(init_file: Path, version: tuple):
        with open(init_file, "r") as file:
            text = file.read()

        version = tuple(version)
        str_version = [str(v) for v in version]
        matcher = '"name".*:.*,'
        name_match = re.findall(matcher, text)
        matcher = '"version".*:.*,'
        version_match = re.findall(matcher, text)
        text = text.replace(name_match[0], f'"name": "Node Pie {".".join(str_version)}",')
        text = text.replace(version_match[0], f'"version": {str(version)},')

        with open(init_file, "w") as file:
            file.write(text)

    def update_constants_file(constants_file, value):
        with open(constants_file, "r") as file:
            text = file.read()

        matcher = '__IS_DEV__.*=.*'
        name_match = re.findall(matcher, text)
        text = text.replace(name_match[0], f'__IS_DEV__ = {str(value)}')

        with open(constants_file, "w") as file:
            file.write(text)

    # def multi_input(prompt=""):
    #     """Get user input over multiple lines. Exit with Ctrl-Z"""
    #     print(prompt)
    #     contents = []
    #     while True:
    #         try:
    #             line = input()
    #         except EOFError:
    #             break
    #         contents.append(line)
    #     return "\n".join(contents)

    # def multi_line_input(prompt):
    #     dark = "#26242f"
    #     win = tkinter.Tk()

    #     w = h = 750

    #     # get screen width and height
    #     ws = win.winfo_screenwidth() # width of the screen
    #     hs = win.winfo_screenheight() # height of the screen

    #     # calculate x and y coordinates for the Tk root window
    #     x = int((ws/2) - (w/2))
    #     y = int((hs/2) - (h/2))

    #     win.geometry(f"{w}x{h}+{x}+{y}")
    #     win.config(bg=dark)

    #     def confirm():
    #         confirm.final_text = text.get("1.0", tkinter.END)
    #         win.quit()

    #     label = tkinter.Label(win, text=prompt)
    #     label.configure(bg=dark, fg="white")
    #     label.pack()

    #     button = tkinter.Button(win, text="Confirm", width=20, command=confirm)
    #     button.pack(side=tkinter.BOTTOM)
    #     button.configure(bg=dark, fg="white")

    #     text = tkinter.Text(win,)
    #     scroll = tkinter.Scrollbar(win)
    #     text.configure(yscrollcommand=scroll.set, bg=dark, fg="white")
    #     text.focus_set()
    #     text.pack(side=tkinter.LEFT, fill=tkinter.BOTH)

    #     scroll.config(command=text.yview)
    #     scroll.pack(side=tkinter.RIGHT, fill=tkinter.BOTH)

    #     win.mainloop()
    #     return confirm.final_text

    # def multi_line_input(prompt):
    #     ctk.set_appearance_mode("dark")
    #     ctk.set_default_color_theme("dark-blue")
    #     win = ctk.CTk()

    #     w = h = 750

    #     # get screen width and height
    #     ws = win.winfo_screenwidth()  # width of the screen
    #     hs = win.winfo_screenheight()  # height of the screen

    #     # calculate x and y coordinates for the Tk root window
    #     x = int((ws / 2) - (w / 2))
    #     y = int((hs / 2) - (h / 2))

    #     win.geometry(f"{w}x{h}+{x}+{y}")

    #     # win.config(bg=dark)

    #     def confirm():
    #         confirm.final_text = textbox.textbox.get("1.0", ctk.END)
    #         win.quit()

    #     label = ctk.CTkLabel(win, text=prompt)
    #     label.pack()

    #     button = ctk.CTkButton(win, text="Confirm", width=20, command=confirm)
    #     button.pack(side=ctk.BOTTOM)
    #     # button.configure(bg=dark, fg="white")

    #     textbox = ctk.CTkTextbox(win)
    #     textbox.focus_set()
    #     textbox.pack(fill=ctk.BOTH, side=ctk.LEFT)
    #     # scroll = ctk.CTkScrollbar(win)

    #     # textbox.configure(width=w - scroll.winfo_width() * 20)
    #     textbox.configure(width=w)

    #     # textbox.configure(yscrollcommand=scroll.set)

    #     # scroll.configure(command=textbox.yview)
    #     # scroll.pack(side=ctk.RIGHT, fill=ctk.BOTH)

    #     win.mainloop()
    #     return confirm.final_text

    def multi_line_input(prompt: str):
        return click.edit(text=prompt, editor="code -w -n", extension=".md")

    def main():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-v",
            "--version",
            help="The version number to use, in the format '0.0.1'",
            default="",
            type=str,
        )
        args = parser.parse_args()

        path = Path(__file__).parent
        files = [Path(f.decode("utf8")) for f in subprocess.check_output("git ls-files", shell=True).splitlines()]
        files = [f for f in files if not any(i in str(f) for i in ["images\\", "README", ".gitignore", "build.py"])]

        # version
        if args.version:
            file_version = args.version.replace(".", "_")
        else:
            res = requests.get("https://api.github.com/repos/strike-digital/node_pie/releases").json()[0]
            latest_version: str = res["tag_name"]
            subversion = latest_version.split(".")[-1]

            file_version = "_".join(latest_version.split(".")[:-1] + [str(int(subversion) + 1)])

        print(file_version)
        update_init_file(path / "__init__.py", tuple(int(f) for f in file_version.split("_")))
        # update_constants_file(constants_file, False)

        out_path = path / "builds" / f"node_pie_{file_version}.zip"

        print(f"Zipping {len(files)} files")
        with ZipFile(out_path, 'w') as z:
            # writing each file one by one
            for file in files:
                print(file, file.exists())
                # print(file)
                # z.write(file, arcname=str(file).replace("asset_bridge", f"asset_bridge_{file_version}"))
                z.write(file, arcname=str(f"node_pie_{file_version}" / file))
        print(f"Zipped: {out_path}")

        try:
            with open("tokens.txt", "r") as f:
                token = f.readlines()[0]
        except Exception:
            webbrowser.open(out_path.parent)
            return

        create_release = input("Do you want to create a release on github? (y/n) ")

        if create_release == "y":
            gh = Github(token)
            repo = gh.get_repo("strike-digital/node_pie")
            version = file_version.replace("_", ".")
            commit = repo.get_commits()[0]

            message = multi_line_input("Release message:")
            release = repo.create_git_tag_and_release(
                tag=version,
                release_name="v" + version,
                release_message=message,
                tag_message=version,
                object=commit.sha,
                type="",
            )
            release.upload_asset(str(out_path))
            webbrowser.open(release.html_url)

        else:
            webbrowser.open(out_path.parent)


if __name__ == "__main__":
    main()