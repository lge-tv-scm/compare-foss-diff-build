import json
import os
import subprocess
import logging
import argparse
import requests


logging.basicConfig(format='%(levelname)-10s: %(message)s')
jenkins_url = os.getenv("JENKINS_URL")
if jenkins_url[-1] == "/":
    jenkins_url = jenkins_url[:-1]

build_archives_root = "/binary/build_results"
build_repo_url = "ssh://wall.lge.com/starfish/build-starfish"


def get_bom_contents(job_name, build_number, image_name="starfish-atsc-flash"):
    job_name_split = job_name.split("-")
    if job_name_split[2] == "official":
        bom_root = "{}/{}/{}/{}/{}/{}/webos-bom.json".format(build_archives_root, "starfish", job_name, build_number, job_name_split[3], image_name)
    else:
        bom_root = "{}/{}/{}/{}/{}/{}/webos-bom.json".format(build_archives_root, "starfish_verifications", job_name, build_number, job_name_split[3], image_name)
    f_bom_file = open(bom_root, 'r')
    f_bom_contents = f_bom_file.read().split('\n')
    f_bom_contents2 = filter(lambda x: x != "", f_bom_contents)
    f_bom_contents3 = list(map(lambda x: x[:-1], f_bom_contents2))
    a = json.loads("[" + ",".join(f_bom_contents3) + "]")
    return a


def create_bom_dict(webos_bom):
    bom_dict = {}
    for each_module in webos_bom:
        bom_dict[each_module['recipe']] = each_module
    return bom_dict


def compare_foss_bom(previous_job, previous_job_number, current_job, current_job_number, image_name="starfish-atsc-flash"):
    job_name_split = current_job.split("-")
    foss_file_name = "foss_list_{}.txt".format(job_name_split[1])

    diff_modules = {}

    if not os.path.isfile(foss_file_name):
        logging.error("{}: {} isnt' created.".format(image_name, foss_file_name))
        foss_file_name = "foss_list.txt"
    logging.warning("{}: {} will be used.".format(image_name, foss_file_name))
    foss_list = open(foss_file_name, 'r').read().split('\n')
    try:
        current_job_bom = get_bom_contents(current_job, current_job_number, image_name)
        previous_job_bom = get_bom_contents(previous_job, previous_job_number, image_name)
    except FileNotFoundError as e:
        logging.error("Doesn't exist " + e.filename)
        return diff_modules

    current_job_bom_dict = create_bom_dict(current_job_bom)
    previous_job_bom_dict = create_bom_dict(previous_job_bom)

    for each_module in foss_list:
        if each_module not in current_job_bom_dict.keys():
            logging.warning("Remove " + each_module + " from foss list")
            if each_module in previous_job_bom_dict.keys():
                diff_modules[each_module] = {
                    "current_extendpkgv": "NA",
                    "previous_extendpkgv": previous_job_bom_dict[each_module]['previous_extendpkgv']
                }
        else:
            if each_module not in previous_job_bom_dict.keys():
                diff_modules[each_module] = {
                    "current_extendpkgv": current_job_bom_dict[each_module]['previous_extendpkgv'],
                    "previous_extendpkgv": "NA"
                }
            else:
                current_extendpkgv = current_job_bom_dict[each_module]['extendpkgv']
                previous_extendpkgv = previous_job_bom_dict[each_module]['extendpkgv']

                if current_extendpkgv != previous_extendpkgv:
                    diff_modules[each_module] = {
                        "current_extendpkgv": current_extendpkgv,
                        "previous_extendpkgv": previous_extendpkgv
                    }
    return diff_modules


def trigger_bdk_build(job_name, build_number, images):
    job_name_split = job_name.split("-")
    build_machine = job_name_split[3]
    build_branch = job_name_split[1]
    logging.warning("Build machine: " + build_machine)
    logging.warning("Branch: " + build_branch)
    logging.warning("Build image: " + str(images))

    build_starfish_commit = "builds/{}/{}".format(build_branch, build_number)
    r = subprocess.check_output("git ls-remote {} {}".format(build_repo_url, build_starfish_commit), shell=True)
    r_list = r.decode("utf-8")[:-1].split('\n')

    # Check if 'build_starfish_commit' exists
    if r_list[0] == '' or len(r_list) != 1:
        logging.error("{} doesn't exist on {}".format(build_starfish_commit, build_repo_url))
        return

    Build_summary = "BDK Build for {} - {}".format(job_name, build_starfish_commit)
    Build_starfish_machine = "Build_starfish_{}".format(build_machine)
    build_codename = build_branch
    region_atsc = True
    extra_images = "starfish-bdk"

    build_params = {
        "token": "trigger_clean_build",
        "Build_summary": Build_summary,
        Build_starfish_machine: True,
        "build_codename": build_codename,
        "region_atsc": True,
        "extra_images": extra_images,
        "webos_local": "WEBOS_DISTRO_BUILD_ID=\"" + str(build_number) + "\"\nSDKMACHINE=\"i686\""
    }

    if build_machine in ['m16', 'm16p', 'm2r', 'k3l', 'k3lp']:
        clean_job_name = "clean-engineering-build-second"
    else:
        clean_job_name = "clean-engineering-build"
    job_build_url = jenkins_url + "/job/" + clean_job_name + "/buildWithParameters"
    logging.warning(job_build_url)
    logging.warning("Build parameters:")
    logging.warning("   " + str(build_params))
    logging.warning("Trigger a clean engineering build for starfish-bdk")
    trigger_result = requests.post(
        job_build_url,
        data=build_params
    )
    logging.warning("Trigger status code: " + str(trigger_result.status_code))
    logging.warning(trigger_result.text)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--jobname", help="Job name", required=True)
    arg_parser.add_argument("--buildnumber", help="Build number", required=True)
    args = arg_parser.parse_args()

    job_name = args.jobname;
    build_number = int(args.buildnumber)
    logging.warning("Build Job: " + job_name)
    logging.warning("Build Number: " + str(build_number))
    image_names = [
        "starfish-atsc-flash-devel",
        "starfish-arib-flash-devel",
        "starfish-dvb-flash-devel"
    ]
    extra_images = []
    for build_image in image_names:
        compare_result = compare_foss_bom(job_name, build_number - 1, job_name, build_number, image_name=build_image)
        if len(compare_result) != 0:
            logging.warning(build_image)
            logging.warning(str(compare_result))
            extra_images.append(build_image)
            break
    if len(extra_images) != 0:
        print("CHANGED")
    else:
        logging.warning("No foss change in {}'s build number {}".format(job_name, build_number))
