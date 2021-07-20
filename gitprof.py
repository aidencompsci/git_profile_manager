#!/usr/bin/env python
import argparse
import os
import subprocess


"""
IMPORTANT JSON FUNCTIONS
"""
import json
def get_dict_from_json(file):
	try:
		with open(file, "r") as file: return dict(json.loads(file.read()))
	except: return dict()

def write_dict_to_json(file, dict):
	try:
		with open(file, "w+") as file: json.dump(dict, file, indent=4, sort_keys=False)
		return True
	except: return False
"""======================"""


"""
CONSTANT or SETUP VALUES
"""
command_series = "Git Profile Manager"
command_name = "gitprof"
version = "v1.0"
version_string = f"{command_series} | {command_name} - {version}"

home = os.getenv("USERPROFILE").replace("\\", "/")
ssh_path = home + "/.ssh/"
git_config_template = "Host *.github.com\n    HostName github.com\n    IdentityFile ~/.ssh/rsa_*"

profiles = {
	"profiles": {},
	"id_list": []
}
profiles_path = home + "/.gitprof_profiles.json"
def get_profiles():
	return get_dict_from_json(profiles_path)
profiles.update(get_profiles())

def update_profiles():
	return write_dict_to_json(profiles_path, profiles)

def add_profile(*args):
	global profiles
	if not len(args) == 3: raise Exception("error adding profile, invalid information provided")
	try:
		username,email,shorthand = args
		profiles["profiles"].setdefault(username, {
			"id_list": [*args],
			"username": username,
			"email": email,
			"shorthand": shorthand
		})
		#json doesn't support sets, just a small hack for now.... it's gross I know
		profiles["id_list"].extend(args)
		temp = set(profiles["id_list"])
		profiles["id_list"] = list(temp)
		return True
	except: return False

def remove_profile(username):
	global profiles
	try:
		kwlist = profiles["profiles"][username]["id_list"]
		for kw in kwlist: #eugh... gross, I know, but it's late and I'm tired
			if kw in profiles["id_list"]:
				profiles["id_list"].remove(kw)
		profiles["profiles"].pop(username)
		return True
	except: return False

#loop through and find ALL profiles that return a match
def get_profiles_from_id(id):
	return [username for username,profile in profiles["profiles"].items() if id in profile["id_list"]]


#checks all id's to find if it has been used before
def is_unique_id(*id_list):
	return not any([id in profiles["id_list"] for id in id_list])

def refresh_keys(_):
	keys = [profile["shorthand"] for k,profile in profiles["profiles"].items()]
	for key in keys:
		ssh_key_found = os.path.isfile(f"{ssh_path}rsa_{key}")
		username = get_profiles_from_id(key)[0]
		if not ssh_key_found:
			print(f"Could not find ssh key for \"{username}\"")
		else:

			with open(ssh_path + "config", "r") as config_file:
				file_string = config_file.read()
				key_host_string = git_config_template.replace("*", key)
			if not key_host_string in file_string:
				print(f"Writing key ({key}) for", username)
				file_string += ("\n" if not file_string[-1] == "\n" else "") + key_host_string
				with open(ssh_path + "config", "w+") as config_file:
					config_file.write(file_string + "\n")

	print("All found keys refreshed")
	return True


def add(args):
	args.shorthand = args.shorthand if args.shorthand is not None else args.username
	unique = is_unique_id(args.username, args.email, args.shorthand)
	should_add = False

	if unique or args.override: should_add = True
	else:
		ans = input("Override an existing profile? [y/n]: ").strip().lower()
		if ans == "y": should_add = True

	if should_add:
		print(f"Added \"{args.username}\"")
		add_profile(args.username, args.email, args.shorthand)
		update_profiles()
		refresh_keys(None)
	else: print("Did not add new profile")

	return should_add

def list_profs(args):
	print("List of profile usernames:")
	print("(use any of these strings to refer to the profile)")
	plist = [(i + 1, username) for i, (username, profile) in enumerate(profiles["profiles"].items()) if
			 (args.key is not None and any([args.key in string if not args.exact else args.key == string for string in profile["id_list"]])) or (args.key is None)]

	if plist:
		for i, u in plist:
			print(f" {i}) {u}")
			if args.verbose:
				profile = profiles["profiles"][u]
				print(f"\t Username: {profile['username']}\n"
					  f"\t    Email: {profile['email']}\n"
					  f"\tShorthand: {profile['shorthand']}")
	else:
		print("No profiles found", end="")
		if args.key is not None: print(" - Try a different key")
		else: print()


def remove(args):
	print("removing", args.id)

	plist = [username for i, (username, profile) in enumerate(profiles["profiles"].items()) if args.id in profile["id_list"]]

	should_remove = args.override
	if not args.override:
		ans = input(f"Remove profiles?\n{plist}\n[y/n]: ").strip().lower()
		if ans == "y": should_remove = True

	if should_remove:
		for username in plist:
			if remove_profile(username): print(f"Removed ... {username}"); update_profiles()
			else: print("Failed to remove")

	return should_remove


def get_current(_):
	pipe = subprocess.Popen(["git", "config", "user.name"], stdout=subprocess.PIPE,
						   								   stderr=subprocess.PIPE)
	out, err = pipe.communicate()
	username = out.decode().replace("\n", "")

	pipe = subprocess.Popen(["git", "config", "user.email"], stdout=subprocess.PIPE,
						   								   stderr=subprocess.PIPE)
	out, err = pipe.communicate()
	email = out.decode().replace("\n", "")

	if username and email:
		try:
			profile = profiles["profiles"][username]
			print(f"Current Profile:")
			print(f"\t Username: {profile['username']}\n"
				  f"\t    Email: {profile['email']}\n"
				  f"\tShorthand: {profile['shorthand']}")
		except:
			print("Current git profile not in profile list, consider adding it")
			print(f"Username: {username} | Email: {email}")
	else:
		print("Error: Perhaps you are not in a git repository.")

#as I am writing this I just realized that the older functions (the one's I added first, add/list/remove)
#might tend to call another function and leave their man one uncluttered... I think I changed styles midway
#through writing this program. In a future version I might rewrite it to be more stylistically consistent,
#but the function should be unaffected
def switch_profile(args):
	print("Switching to", args.id)

	plist = [username for i, (username, profile) in enumerate(profiles["profiles"].items()) if
			 args.id in profile["id_list"]]
	username = plist[0]

	should_switch = args.override
	if not args.override:
		ans = input(f"Switch to profile?\n{username}\n[y/n]: ").strip().lower()
		if ans == "y": should_switch = True

	if should_switch:
		profile = profiles["profiles"][username]
		os.system(f"git config user.name \"{profile['username']}\"")
		os.system(f"git config user.email \"{profile['shorthand']}\"")
		print(f"Switched to profile ({username})")


def clone_repo(args):
	username = get_profiles_from_id(args.id)[0]
	email = profiles["profiles"][username]["email"]
	args.repo = args.repo.replace("git@github.com", f"git@{args.id}.github.com")

	os.system(f"git clone {args.repo}")

	#will it always have a .git on the end? If I use ssh links I think it will
	#but in the future I would like a more foolproof method...
	sub_folder = args.repo.split("/")[1][:-4] + "/"
	os.chdir(sub_folder)

	os.system(f'git config user.name "{username}"')
	os.system(f'git config user.email "{email}"')

	print("Cloned and set config")

"""
Commandline Arg-parsing
"""

parser = argparse.ArgumentParser(description="Manager your Git profiles")
parser.add_argument("-v", "-version", action="version", version=version_string)
parser.set_defaults(func=lambda *x: print(version_string))
#kinda redundent, I know, but I don't want it to spit an error.... maybe I'll make it run help by default? will change later

sub_parser = parser.add_subparsers()

"""ADD PROFILE COMMAND"""
parser_add = sub_parser.add_parser("add", aliases=("a"))
parser_add.add_argument("-u", "-user", "-username", dest="username", required=True, help="a git profile username")
parser_add.add_argument("-e", "-email", dest="email", required=True, help="a git profile email")
parser_add.add_argument("-s", "-shorthand", dest="shorthand", help="shorthand that makes identifying this profile quicker for you, will default to username")
parser_add.add_argument("-o", "-override", action="store_true", dest="override", help="if duplicate profile info is found, overwrite without prompting confirmation")
parser_add.set_defaults(func=add)

"""REMOVE PROFILE COMMAND"""
parser_remove = sub_parser.add_parser("remove", aliases=("r", "rm"))
parser_remove.add_argument("-i", "-id", "-identifier", dest="id", required=True, help="username, email, or shorthand of profile to remove")
parser_remove.add_argument("-o", "-override", action="store_true", dest="override", help="automatically removes without prompting confirmation")
parser_remove.set_defaults(func=remove)

"""LIST PROFILES COMMAND"""
parser_list = sub_parser.add_parser("list", aliases=("l"))
parser_list.add_argument("-v", "-verbose", action="store_true", dest="verbose", help="list detailed information, besides just username")
parser_list.add_argument("-e", "-exact", action="store_true", dest="exact", help="use only an exact keymatch, versus the default substring match")
parser_list.add_argument("-k", "-key", "-keyword", dest="key", help="will only list profiles that have a pattern match to this keyword")
parser_list.set_defaults(func=list_profs)

"""REFRESH PROFILE KEYS COMMAND"""
#open to shorthand suggustions lol
#ref does not seem to be a valid choice and I'm not sure why. It won't let me use this option
parser_refresh = sub_parser.add_parser("refresh", aliases=("ref"))
parser_refresh.set_defaults(func=refresh_keys)

"""CURRENT PROFILE COMMAND"""
parser_current = sub_parser.add_parser("current", aliases=("c", "local", "dir", "ls", "path",
														   "file", "folder", "f", "project", "proj"))
parser_current.set_defaults(func=get_current)

"""SWITCH PROFILE COMMAND"""
parser_switch = sub_parser.add_parser("switch", aliases=("sw"))
parser_switch.add_argument("-i", "-id", "-identifier", dest="id", required=True, help="username, email, or shorthand of profile to switch to")
parser_switch.add_argument("-o", "-override", action="store_true", dest="override", help="automatically switch to first profile match for id")
parser_switch.set_defaults(func=switch_profile)

"""GIT CLONE WRAPPER"""
parser_clone = sub_parser.add_parser("clone", aliases=("cl"))
parser_clone.add_argument("-i", "-id", "-identifier", dest="id", required=True, help="username, email, or shorthand of profile to download from")
parser_clone.add_argument("-r", "-repo", dest="repo", required=True, help="ssh link to the repo")
parser_clone.set_defaults(func=clone_repo)

"""
=== implemented ===
gitprof add
gitprof list
gitprof remove
gitprof version
gitprof refresh
gitprof clone
gitprof current
gitprof switch 

=== not implemented ===
gitprof edit 
	(like you could edit a profile as long as you have one of the three keys?)
	(alternate solutions are to remove it and re-add it...)

"""

args = parser.parse_args()
args.func(args)

#would I need something about __name__ == "__main__" ?
#not sure, I mean it's a commandline program... not meant to be imported...
#I guess if you break it it's your fault... :) help
