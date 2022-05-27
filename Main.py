# '''
# Created on May 22, 2022
#
# Personal Tool (gt)
#
#
# @author: MikePanitz
#
# '''
### TODO LIST ##########################################################################################################
# Refactor into argparse'd main


import argparse
import datetime
import os
import sys

from colorama import init
init()

# import stackprinter
# stackprinter.set_excepthook(style='darkbg2')
#
# # from icecream import install
# # install()

from finance.venmo import ConvertVenmoStatement

# #region Functions to handle menu options
# def fnPrepAutograde(args):
#     print(
#         f'\nAUTOGRADER MODE:\n\tSRC:\t{args.SRC}\n\tTidying up SRC in preparation for grading, then auto-grading it\n')
#
#     if not os.path.isdir(args.SRC):
#         print("'SRC' argument must be a directory but isn't")
#         print(f"\tSRC: {args.SRC}\n")
#         sys.exit()
#
#     # consolidate & organize the submissions:
#     allSubs = ConsolidateSubmissions(args.SRC)
#
#     print("=== Submissions Consolidated ===\n")
#
#     start = datetime.datetime.now()
#
#     fpADesc = os.path.join(
#         args.SRC, "Assign.config.json")
#     AssignDesc = LoadConfigFile(fpADesc)
#
#     #  allow command line to override config file for where to put output
#     if args.DEST is not None:
#         AssignDesc['output_dir'] = args.DEST
#
#     print("Loaded the following config files:")
#     for fpConfigFile in AssignDesc[SZ_CONFIG_FILE_LIST_KEY]:
#         print(f"\t{fpConfigFile}")
#     print("")
#
#     if "assignment_type" not in AssignDesc:
#         raise GradingToolError(
#             "Could not find the 'assignment_type' key in the config files!")
#
#     if AssignDesc["assignment_type"] == "BIT_116_Assignment":
#         if args.GenerateGradesheet:
#             AssignDesc["handler_init"]["Javascript_Handler"]["GenerateGradesheet"] = True
#         else:
#             AssignDesc["handler_init"]["Javascript_Handler"]["GenerateGradesheet"] = False
#
#     if args.GenerateGradesheet and \
#             (AssignDesc["assignment_type"] == "BIT_142_Assignment" or \
#              AssignDesc["assignment_type"] == "BIT_143_PCE"):
#         raise GradingToolError("BIT 142 / 143 autograders don't (yet) support the 'generate blank gradesheet' option")
#
#     DoAutoGrading(allSubs, AssignDesc)
#
#     end = datetime.datetime.now()
#     elapsedTime = end - start
#     TotalDuration = str(elapsedTime).split('.', 2)[0]
#     print("Just autograding (not consolidating) took " +
#           TotalDuration + "\n")
#
#
# def fnPrepConsolidate(args):
#     print('\nCONSOLIDATE MODE: Tidying up SRC in preparation for grading')
#     print('\tSRC:\t' + args.SRC + "\n")
#
#     if not os.path.isdir(args.SRC):
#         print("'SRC' argument must be a directory but isn't")
#         print(f"\tSRC: {args.SRC}\n")
#         sys.exit()
#
#     OrganizeSubmissions(args.SRC)
#
# def fnPrepExamList(args):
#     print('\nEXAMS MODE: Listing possible exams to generate:\n\n')
#     ListExams()
#
# def fnPrepExamGen(args):
#     print('\nEXAM GENERATION MODE: Creating exam .pdf (and possibly grading guide .pdf)\n\n')
#     if args.EXAM is None:
#         printError("First parameter is required!")
#         return
#
#     GenerateExam(args.EXAM, args.DEST, args.studentName, args.verbose)
#
#
# def fnPrepCopyRevisionFeedback(args):
#     print('\nREVISE MODE: Copying feedback files (and renaming them to match new revision name)')
#     if args.DEST is None:
#         printError(
#             "Second parameter is required! (only given " + args.SRC + ")")
#         return
#     print('\tSRC:\t' + args.SRC + "\n\tDEST:\t" + args.DEST + "\n")
#     if not os.path.exists(args.SRC):
#         printError('Unable to find ' + args.SRC)
#         return
#     if not os.path.isdir(args.SRC):
#         printError("'SRC' argument must be a directory but isn't")
#         print(f"\tSRC: {args.SRC}\n")
#         sys.exit()
#
#     if not os.path.exists(args.DEST):
#         printError('Unable to find ' + args.DEST)
#         return
#     if not os.path.isdir(args.DEST):
#         printError("'DEST' argument must be a directory but isn't")
#         print(f"\tDEST: {args.DEST}\n")
#         sys.exit()
#
#     CopyRevisionFeedback(args.SRC, args.DEST)
#
#
# def fnPrepCopyTemplate(args):
#     print('\nTEMPLATE MODE: Copying template file to student dirs (and renaming them)')
#     if args.DEST is None:
#         print("Second parameter is required! (only given " + args.SRC + ")")
#         return
#
#     print('\tSRC:\t' + args.SRC + "\n\tDEST:\t" +
#           args.DEST + "\n\tprefix:" + args.prefix + "\n")
#
#     if not os.path.isfile(args.SRC):
#         print("'SRC' argument must be a file but isn't")
#         print(f"\tSRC: {args.SRC}\n")
#         print(
#             "(Perhaps you meant to use the -r option, to copy revision feedback?)\n")
#         sys.exit()
#
#     if not os.path.isdir(args.DEST):
#         print("'DEST' argument must be a directory but isn't")
#         print(f"\tDEST: {args.DEST}\n")
#         sys.exit()
#
#     CopyTemplateToStudents(args.SRC, args.DEST, args.prefix)
#
# #endregion
#
# # The 'CLI' function is used by the overall GradingTool program (it's needed to package stuff using PyZip)
# # TODO: Not using PyZip anymore.  Can I remove CLI() function?
# def CLI():
#
# #region Set up argparse
#     root_parser = argparse.ArgumentParser(
#         description='GradingTool: Automate repetitive grading tasks (Version ' + VERSION + ')')
#
#     subparsers = root_parser.add_subparsers(dest='command', help='sub-command help')
#
#     parser_verbose = argparse.ArgumentParser(add_help=False)
#     parser_verbose.add_argument('-v', '--verbose', action='store_true',
#                                 help='For additional, more detailed output')
#
#     parser_src = argparse.ArgumentParser(add_help=False)
#     parser_src.add_argument('SRC', help='the source directory')
#
#     parser_src_dest = argparse.ArgumentParser(add_help=False, parents=[parser_src])
#     parser_src_dest.add_argument('DEST', help='the destination directory')  # , nargs='?')
#
#
#     szSummary: str
#     szHelp: str
#
#
#     ################################# EXAM GENERATION ################################################
#     def setup_exam_gen_parsers(subparsers):
#         szSummary = 'Exam generation'
#         szHelp = 'Tools to simplify random exam generation'
#         parser_exams = subparsers.add_parser('exams',
#                                                 aliases=['e'],
#                                                 parents=[parser_verbose],
#                                                 help=szSummary,
#                                                 description=szHelp)
#
#         exam_gen_subparsers = parser_exams.add_subparsers(dest='subcommand',
#                                                                    help="Help for the GitHub Classroom parser")
#         szSummary = 'Generate exam from LaTeX source'
#         szHelp = 'Generate exam from LaTeX source, as described in ~/.gradingtool/gradingtool.json.  C.f. the -s parameter'
#         parser_exam_gen = exam_gen_subparsers.add_parser('generate_exam',
#                                                 aliases=['g'],
#                                                 parents=[parser_verbose],
#                                                 help=szSummary,
#                                                 description=szHelp)
#         parser_exam_gen.add_argument('EXAM', help='The exam code (e.g., 2m for BIT142-Midterm) ~OR~ MAKE_CONFIG_FILE to generate a sample config file.')
#
#         parser_exam_gen.add_argument('-s', '--studentName',  # action='store', to store the string
#                                      help='optional parameter for the --ExamGen option: name of student to generate the file for (ex: \"Smith, Jo\")')
#         parser_exam_gen.set_defaults(func=fnPrepExamGen)
#
#         szSummary = 'List possible exams'
#         szHelp = 'List exams from LaTeX source, as described in ~/.gradingtool/gradingtool.json'
#         parser_exam_list = exam_gen_subparsers.add_parser('exam_list',
#                                                 aliases=['l'],
#                                                 parents=[parser_verbose],
#                                                 help=szSummary,
#                                                 description=szHelp)
#         parser_exam_list.set_defaults(func=fnPrepExamList)
#
#
#     setup_exam_gen_parsers(subparsers)
#
#     ################################# MISC. FILE MANIPULATORS ################################################
#     def setup_misc_file_parsers(subparsers):
#         szSummary = 'Misc. file subcommands'
#         szHelp = 'Commands for working with files (regardless of where they came from)'
#         misc_files = subparsers.add_parser('files',
#                                             aliases=['f'],
#                                             help=szSummary,
#                                             description=szHelp)
#         misc_files_subparsers = misc_files.add_subparsers(dest='subcommand', help="Help for the canvas parser")
#
#         parser_files_template_copy_to_subdir = misc_files_subparsers.add_parser('copyToSubdir',
#                                                          aliases=['c'],
#                                                          help='Copy the given file to all the subdirs in DEST')
#         parser_files_template_copy_to_subdir.add_argument('template_file', help='The file.  Will be renamed to include the subdir\'s name')
#         parser_files_template_copy_to_subdir.add_argument('SRC', help='The directory that contains the subdirs.  File will be copied to ALL subdirs')
#         parser_files_template_copy_to_subdir.set_defaults(func=MiscFilesHelper.fn_misc_files_copy_to_subdir)
#
#         parser_files_template_copier = misc_files_subparsers.add_parser('template',
#                                                          aliases=['t'],
#                                                          help='Copy all the files given by TEMPLATE into any feedback files in SRC')
#         parser_files_template_copier.add_argument('template_file', help='The template file')
#         parser_files_template_copier.add_argument('SRC', help='The directory that contains the files to copy the template into')
#         parser_files_template_copier.set_defaults(func=MiscFilesHelper.fn_misc_files_copy_template)
#
#         parser_files_feedback_copier = misc_files_subparsers.add_parser('move_feedback',
#                                                          aliases=['m'],
#                                                          help='Move all the instructor feedback files in SRC to the matching student dir in DEST')
#         parser_files_feedback_copier.add_argument('SRC', help='The directory that contains the instructor\'s feedback files (file names contain/are similar to student dest dir)')
#         parser_files_feedback_copier.add_argument('DEST', help='The directory that contains the student dirs (the dir names must be similar to the instuctor\'s feedback file names)')
#         parser_files_feedback_copier.add_argument('-c', "--confirm", action="store_true",
#                                                   help='Ask before moving each file (default is to move to whatever the "best" match is, which can be random for files without student names in them)')
#
#         parser_files_feedback_copier.set_defaults(func=MiscFilesHelper.fn_misc_files_move_feedback_to_student_dirs)
#
#     setup_misc_file_parsers(subparsers)
#
#     ################################# LIST COURSES, ASSIGNMENTS AND GITHUB/CANVASAPI ACCESS ##################
#     def setup_list_info_parsers(subparsers):
#         szSummary = 'List info'
#         szHelp = f'List all the homework assignments in gradingtool.json'
#         list_info = subparsers.add_parser('list',
#                                             aliases=['l'],
#                                             help=szSummary,
#                                             description=szHelp)
#         list_info.add_argument('-c', '--COURSE',
#                                 help='Name of the course (e.g., 142), leave out for all courses')
#
#         list_info.set_defaults(func=Canvas_API_Helper.fn_canvas_api_list_homeworks)
#
#     setup_list_info_parsers(subparsers)
#
#     ################################# Canvas ################################################
#     def setup_canvas_parsers(subparsers):
#         config = get_app_config()
#         dir_for_new_feedbacks, zip_file_name = config.verify_keys([
#             "canvas/NewDirForMissingFeedbackFiles",
#             "canvas/ZipFileToUploadToCanvas"
#         ])
#
#         szSummary = 'Canvas subcommands'
#         szHelp = 'Commands for working with the CanvasAPI (download), and with files bulk-downloaded from Canvas'
#         parser_canvas = subparsers.add_parser('canvas',
#                                                         aliases=['c'],
#                                                         help=szSummary,
#                                                         description=szHelp)
#
#         canvas_subparsers = parser_canvas.add_subparsers(dest='subcommand', help="Help for the canvas parser")
#         parser_ag = canvas_subparsers.add_parser('autograde',
#                                               aliases=['a'],
#                                               help='Organize the SRC dir, then autograde each student folder within it')
#         parser_ag.add_argument('SRC', help='The directory that contains the files to organize and autograde')
#         parser_ag.add_argument('-d', '--DEST', help='Directory to put the output files into; defaults to OUTPUT within SRC')
#         parser_ag.set_defaults(func=CanvasHelper.fn_canvas_autograde)
#
#
#         parser_download_homeworks = canvas_subparsers.add_parser('download',
#                                                                      aliases=['d'],
#                                                                      help=f'Download new student homework submissions and update existing subs (using the CanvasAPI)')
#         parser_download_homeworks.add_argument('COURSE',
#                                                help='Name of the course (e.g., 142), or \'all\' for all sections')
#         parser_download_homeworks.add_argument('HOMEWORK_NAME',
#                                                help='The name of the homework assignment (or "all", to download all assignments for this class)')
#         parser_download_homeworks.add_argument('-d', '--DEST',
#                                                help='Directory to download homework into and/or update existing repos')
#         parser_download_homeworks.add_argument('-q', '--QUARTER',
#                                                help='Quarter code to look for (e.g., "S20" for Spring 2020)')
#         parser_download_homeworks.set_defaults(func=Canvas_API_Helper.fn_canvas_api_download_homework)
#
#
#         parser_canvas_org = canvas_subparsers.add_parser('organize',
#                                                  aliases=['o'],
#                                                  help='Organize Canvas files within a directory or .ZIP file')
#         parser_canvas_org.add_argument('SRC', help='The directory that contains the files to organize -OR- the zip file to extract into a subdir, and then organize')
#         parser_canvas_org.add_argument('-d', '--DEST',
#                                help='Directory to extract a .ZIP file into; defaults to same dir as the .ZIP file')
#         parser_canvas_org.set_defaults(func=CanvasHelper.fn_canvas_organize_files)
#
#         parser_canvas_org = canvas_subparsers.add_parser('revisions',
#                                                  aliases=['r'],
#                                                  help='Copy original feedbacks into new, revised student submissions')
#         parser_canvas_org.add_argument('SRC', help='The directory that contains the original feedback files')
#         parser_canvas_org.add_argument('DEST', help='The directory that contains the new homeworks to upload')
#         parser_canvas_org.set_defaults(func=CanvasHelper.fn_canvas_copy_feedback_to_revision)
#
#         parser_canvas_template_copier = canvas_subparsers.add_parser('template',
#                                                                         aliases=['t'],
#                                                                         help='Copy all the files given by TEMPLATE into any feedback files in SRC, then create a _NEW folder with templates for students who didn\'t include the feedback file')
#
#         parser_canvas_template_copier.add_argument('template_file', help='The template file')
#         parser_canvas_template_copier.add_argument('SRC',
#                                                   help='The directory that contains the files to copy the template into (the "_NEW" dir will be created in here')
#         parser_canvas_template_copier.set_defaults(func=CanvasHelper.fn_canvas_copy_template)
#
#         parser_canvas_package_ = canvas_subparsers.add_parser('package',
#                                                                 aliases=['p'],
#                                                                 help=f'Package all feedback files to upload to Canvas.  All files from Canvas are put into a .ZIP (named {dir_for_new_feedbacks}), new feedback files are put into a new directory (named {zip_file_name})')
#         parser_canvas_package_.add_argument('SRC',
#                                             help='The directory that contains the feedback files to upload')
#         parser_canvas_package_.set_defaults(func=CanvasHelper.fn_canvas_package_feedback_for_upload)
#
#
#     # now let's actually install these:
#     setup_canvas_parsers(subparsers)
#
#
#     # ################################# Canvas via API ################################################
#     # def setup_canvas_api_parsers(subparsers):
#     #
#     #     szSummary = 'Canvas (REST API) subcommands'
#     #     szHelp = 'Commands for working with Canvas, via their web API'
#     #     parser_github_classroom = subparsers.add_parser('CanvasAPI',
#     #                                                     aliases=['ca'],
#     #                                                     help=szSummary,
#     #                                                     description=szHelp)
#     #     canvas_api_subparsers = parser_github_classroom.add_subparsers(dest='subcommand', help="Help for the canvas API parser")
#     #
#     #
#     #     parser_download_homeworks = canvas_api_subparsers.add_parser('download',
#     #                                                              aliases=['d'],
#     #                                                              help=f'Download new student homework submissions and update existing subs')
#     #     parser_download_homeworks.add_argument('COURSE',
#     #                                            help='Name of the course (e.g., 142), or \'all\' for all sections')
#     #     parser_download_homeworks.add_argument('HOMEWORK_NAME',
#     #                                            help='The name of the homework assignment (or "all", to download all assignments for this class)')
#     #     parser_download_homeworks.add_argument('-d', '--DEST',
#     #                                            help='Directory to download homework into and/or update existing repos')
#     #     parser_download_homeworks.add_argument('-q', '--QUARTER',
#     #                                      help='Quarter code to look for (e.g., "S20" for Spring 2020)')
#     #     parser_download_homeworks.set_defaults(func=Canvas_API_Helper.fn_canvas_api_download_homework)
#     #
#     #
#     #     # parser_ag = canvas_api_subparsers.add_parser('autograde',
#     #     #                                          aliases=['a'],
#     #     #                                          help='Autograde each student folder within the SRC dir')
#     #     # parser_ag.add_argument('SRC', help='The directory that contains the files to organize and autograde')
#     #     # parser_ag.add_argument('-d', '--DEST',
#     #     #                        help='Directory to put the output files into; defaults to OUTPUT within SRC')
#     #     # parser_ag.set_defaults(func=GitHubClassroomHelper.ghc_autograde)
#     #     #
#     #     #
#     #     # parser_grading_list = canvas_api_subparsers.add_parser('gradinglist',
#     #     #                                                    aliases=['l'],
#     #     #                                                    help="Get lists indicating which assignments don't have feedback" \
#     #     #                                                         ", which have feedback but have been modified since then, and " \
#     #     #                                                         "which have been graded and are unchanged")
#     #     # parser_grading_list.add_argument('COURSE',
#     #     #                                  help='Name of the course (e.g., bit142), or \'all\' for all sections')
#     #     # parser_grading_list.add_argument('HOMEWORK_NAME',
#     #     #                                  help='The name of the homework assignment (or "all", for all assignments)')
#     #     # parser_grading_list.add_argument('-d', '--DEST',
#     #     #                                  help='Directory containing existing repos')
#     #     # parser_grading_list.set_defaults(func=GitHubHelper.fn_github_grading_list)
#     #     #
#     #     #
#     #     # parser_canvas_template_copier = canvas_api_subparsers.add_parser('template',
#     #     #                                                                  aliases=['t'],
#     #     #                                                                  help='Copy all the files given by TEMPLATE into any feedback files in SRC, then create a _NEW folder with templates for students who didn\'t include the feedback file')
#     #     #
#     #     # parser_canvas_template_copier.add_argument('template_file', help='The template file')
#     #     # parser_canvas_template_copier.add_argument('SRC',
#     #     #                                            help='The directory that contains the files to copy the template into (the "_NEW" dir will be created in here')
#     #     # parser_canvas_template_copier.set_defaults(func=CanvasHelper.fn_canvas_copy_template)
#     #     #
#     #     #
#     #     # parser_canvas_org = canvas_api_subparsers.add_parser('revisions',
#     #     #                                                  aliases=['r'],
#     #     #                                                  help='Copy original feedbacks into new, revised student submissions')
#     #     # parser_canvas_org.add_argument('SRC', help='The directory that contains the original feedback files')
#     #     # parser_canvas_org.add_argument('DEST', help='The directory that contains the new homeworks to upload')
#     #     # parser_canvas_org.set_defaults(func=CanvasHelper.fn_canvas_copy_feedback_to_revision)
#     #     #
#     #     #
#     #     # parser_canvas_package_ = canvas_api_subparsers.add_parser('upload',
#     #     #                                                       aliases=['u'],
#     #     #                                                       help=f'Upload all feedback files to Canvas.')
#     #     # parser_canvas_package_.add_argument('SRC',
#     #     #                                     help='The directory that contains the feedback files to upload')
#     #     # parser_canvas_package_.set_defaults(func=CanvasHelper.fn_canvas_package_feedback_for_upload)
#     #
#     #
#     # setup_canvas_api_parsers(subparsers)
#     stopCodeFoldingHere = True
#
#     ################################# GitHub Classroom ################################################
#     def setup_git_parsers(subparsers):
#         szSummary = 'git-related subcommands'
#         szHelp = 'Commands for working with git locally, with GitHub directly, and with files bulk-downloaded from GitHub (via GitHub Classroom)'
#         parser_git = subparsers.add_parser('git',
#                                                         aliases=['g'],
#                                                         help=szSummary,
#                                                         description=szHelp)
#         git_subparsers = parser_git.add_subparsers(dest='subcommand',
#                                                                    help="Help for the GitHub Classroom parser")
#
#         parser_ag = git_subparsers.add_parser('autograde',
#                                                  aliases=['a'],
#                                                  help='Local git: Autograde each student folder within the SRC dir')
#         parser_ag.add_argument('SRC', help='The directory that contains the files to organize and autograde')
#         parser_ag.add_argument('-d', '--DEST', help='Directory to put the output files into; defaults to OUTPUT within SRC')
#         parser_ag.set_defaults(func=GitHubClassroomHelper.ghc_autograde)
#
#
#         parser_delete_repos = git_subparsers.add_parser('delete_repos',
#                                                               help=f'GitHub: Remove all student repos from a given organization in GitHub (for post-quarter cleanup and subsequent reuse')
#         parser_delete_repos.add_argument('COURSE',
#                                             help='The course to clean out')
#         parser_delete_repos.set_defaults(func=GitHubHelper.fn_github_delete_student_repos)
#
#
#         parser_download_homeworks = git_subparsers.add_parser('download',
#                                                               aliases=['d'],
#                                                               help=f'GitHub: Clone new student homework repos from GitHub, pull changes for existing repos')
#         parser_download_homeworks.add_argument('COURSE',
#                                             help='Name of the course (e.g., 142), or \'all\' for all sections')
#         parser_download_homeworks.add_argument('HOMEWORK_NAME',
#                                             help='The name of the homework assignment (or "all", to download all assignments for this class)')
#         parser_download_homeworks.add_argument('-d', '--DEST',
#                                help='Directory to download homework into and/or update existing repos')
#         parser_download_homeworks.add_argument('-n', '--NEWONLY',
#                                                action='store_true',
#                                help='Only download repos that have changed since last graded (or that haven\'t been graded)')
#         parser_download_homeworks.set_defaults(func=GitHubHelper.fn_github_download_homework)
#
#
#         parser_fixup = git_subparsers.add_parser('fixup_ghc',
#                                                     aliases=['f'],
#                                                     help='Local files: Fix the GitHub Classroom URLs into real usable URLs')
#         parser_fixup.add_argument('SRC', help='The directory that contains the repos to fixup')
#
#         def fixup_repos(args):
#             GitHubClassroomHelper.go_through_all_git_repos(args.SRC, GitHubClassroomHelper.ghc_fix_repo)
#
#         parser_fixup.set_defaults(func=fixup_repos)
#
#         parser_grading_list = git_subparsers.add_parser('gradinglist',
#                                                               aliases=['l'],
#                                                               help="GitHub: Get lists indicating which assignments don't have feedback"\
#                                                                 ", which have feedback but have been modified since then, and "\
#                                                                 "which have been graded and are unchanged")
#         parser_grading_list.add_argument('COURSE',
#                                             help='Name of the course (e.g., bit142), or \'all\' for all sections')
#         parser_grading_list.add_argument('HOMEWORK_NAME',
#                                             help='The name of the homework assignment (or "all", for all assignments)')
#         parser_grading_list.add_argument('-d', '--DEST',
#                                help='Directory containing existing repos')
#         parser_grading_list.set_defaults(func=GitHubHelper.fn_github_grading_list)
#
#
#         parser_send = git_subparsers.add_parser('send',
#                                                    aliases=['s'],
#                                                    help='Local git: Sending feedback (add, commit, push) for all repos under ')
#         parser_send.add_argument('SRC', help='The directory that contains the repos to push')
#         parser_send.add_argument('-m', '--message', help='Commit message to use')
#
#         def send_repos(args):
#             GitHubClassroomHelper.go_through_all_git_repos(args.SRC,
#                                                            lambda: GitHubClassroomHelper.ghc_send_feedback(args.message))
#
#         parser_send.set_defaults(func=send_repos)
#
#         parser_do = git_subparsers.add_parser('do',
#                                                  help='TLocal git: reat the rest of the command line as a shell command to be run in each repo')
#         parser_do.add_argument('SRC', help='The directory that contains the repos to "do" the git command in')
#         parser_do.add_argument('CMD_LINE', nargs='*',
#                                help='The \'do\' command will treat anything else as the shell command to execute in the root dir of each repo')
#
#         def do_git_cmd_in_repos(args):
#             GitHubClassroomHelper.go_through_all_git_repos(args.SRC,
#                                                            lambda: GitHubClassroomHelper.ghc_do_cmd_in_repo(args.CMD_LINE))
#         parser_do.set_defaults(func=do_git_cmd_in_repos)
#
#
#         # parser_test = git_subparsers.add_parser('test',
#         #                                          aliases=['t'],
#         #                                          help='Testing the PyGitHub API')
#         # parser_test.set_defaults(func=GitHubHelper.test_PyGitHub)
#
#     setup_git_parsers(subparsers)
#
#     # GH classroom and GH parsers were mereged into 'git' cateogry, above
#     # def setup_github_classroom_parsers(subparsers):
#     #     szSummary = 'GitHub Classroom subcommands'
#     #     szHelp = 'Commands for working with files bulk-downloaded from GitHub, presumably via GitHub Classroom'
#     #     parser_github_classroom = subparsers.add_parser('GitHubClassroom',
#     #                                                     aliases=['g'],
#     #                                                     help=szSummary,
#     #                                                     description=szHelp)
#     #     github_subparsers = parser_github_classroom.add_subparsers(dest='subcommand', help="Help for the GitHub Classroom parser")
#     #
#     #     parser_ag = github_subparsers.add_parser('autograde',
#     #                                           aliases=['a'],
#     #                                           help='Autograde each student folder within the SRC dir')
#     #     parser_ag.add_argument('SRC', help='The directory that contains the files to organize and autograde')
#     #     parser_ag.add_argument('-d', '--DEST', help='Directory to put the output files into; defaults to OUTPUT within SRC')
#     #     parser_ag.set_defaults(func=GitHubClassroomHelper.ghc_autograde)
#     #
#     #     parser_fixup = github_subparsers.add_parser('fixup_ghc',
#     #                                              aliases=['f'],
#     #                                              help='Fix the GH Classroom URLs into real usable URLs')
#     #     parser_fixup.add_argument('SRC', help='The directory that contains the repos to fixup')
#     #     def fixup_repos(args):
#     #         GitHubClassroomHelper.go_through_all_git_repos(args.SRC, GitHubClassroomHelper.ghc_fix_repo)
#     #     parser_fixup.set_defaults(func=fixup_repos)
#     #
#     #     parser_send = github_subparsers.add_parser('send',
#     #                                              aliases=['s'],
#     #                                              help='Sending feedback (add, commit, push) for all repos under ')
#     #     parser_send.add_argument('SRC', help='The directory that contains the repos to push')
#     #     parser_send.add_argument('-m', '--message', help='Commit message to use')
#     #     def send_repos(args):
#     #         GitHubClassroomHelper.go_through_all_git_repos(args.SRC, lambda: GitHubClassroomHelper.ghc_send_feedback(args.message))
#     #     parser_send.set_defaults(func=send_repos)
#     #
#     #     parser_do = github_subparsers.add_parser('do',
#     #                                              aliases=['d'],
#     #                                              help='Treat the rest of the command line as a shell command to be run in each repo')
#     #     parser_do.add_argument('SRC', help='The directory that contains the repos to "do" the git command in')
#     #     parser_do.add_argument('CMD_LINE',  nargs='*',
#     #                                         help='The \'do\' command will treat anything else as the shell command to execute in the root dir of each repo')
#     #
#     #     def do_git_cmd_in_repos(args):
#     #         GitHubClassroomHelper.go_through_all_git_repos(args.SRC, lambda: GitHubClassroomHelper.ghc_do_cmd_in_repo(args.CMD_LINE))
#     #     parser_do.set_defaults(func=do_git_cmd_in_repos)
#     #
#     #
#     # setup_github_classroom_parsers(subparsers)
#
#     # def setup_github_parsers(subparsers):
#     #     szSummary = 'GitHub (the server/website) subcommands'
#     #     szHelp = 'Commands for working with GitHub'
#     #     parser_github_classroom = subparsers.add_parser('GitHub',
#     #                                                     aliases=['gh'],
#     #                                                     help=szSummary,
#     #                                                     description=szHelp)
#     #     github_subparsers = parser_github_classroom.add_subparsers(dest='subcommand', help="Help for the canvas parser")
#     #
#     #     parser_test = github_subparsers.add_parser('test',
#     #                                              aliases=['t'],
#     #                                              help='Testing the PyGitHub API')
#     #     parser_test.set_defaults(func=GitHubHelper.test_PyGitHub)
#     #
#     #     parser_delete_repos = github_subparsers.add_parser('delete_repos',
#     #                                                           help=f'Remove all student repos from a given organization (for post-quarter cleanup and subsequent reuse')
#     #     parser_delete_repos.add_argument('COURSE',
#     #                                         help='The course to clean out')
#     #     parser_delete_repos.set_defaults(func=GitHubHelper.fn_github_delete_student_repos)
#     #
#     #
#     #     parser_download_homeworks = github_subparsers.add_parser('download',
#     #                                                           aliases=['d'],
#     #                                                           help=f'Clone new student homework repos, pull changes for existing repos')
#     #     parser_download_homeworks.add_argument('COURSE',
#     #                                         help='Name of the course (e.g., 142), or \'all\' for all sections')
#     #     parser_download_homeworks.add_argument('HOMEWORK_NAME',
#     #                                         help='The name of the homework assignment (or "all", to download all assignments for this class)')
#     #     parser_download_homeworks.add_argument('-d', '--DEST',
#     #                            help='Directory to download homework into and/or update existing repos')
#     #     parser_download_homeworks.set_defaults(func=GitHubHelper.fn_github_download_homework)
#     #
#     #
#     #     parser_grading_list = github_subparsers.add_parser('gradinglist',
#     #                                                           aliases=['l'],
#     #                                                           help="Get lists indicating which assignments don't have feedback"\
#     #                                                             ", which have feedback but have been modified since then, and "\
#     #                                                             "which have been graded and are unchanged")
#     #     parser_grading_list.add_argument('COURSE',
#     #                                         help='Name of the course (e.g., bit142), or \'all\' for all sections')
#     #     parser_grading_list.add_argument('HOMEWORK_NAME',
#     #                                         help='The name of the homework assignment (or "all", for all assignments)')
#     #     parser_grading_list.add_argument('-d', '--DEST',
#     #                            help='Directory containing existing repos')
#     #     parser_grading_list.set_defaults(func=GitHubHelper.fn_github_grading_list)
#     #
#     # # now let's actually install these:
#     # setup_github_parsers(subparsers)
#
#     ################################# StudentTracker ################################################
#
#     def setup_student_tracker_parsers(subparsers):
#         szSummary = 'First consolidate, then autograde homework submissions'
#         szHelp = 'First consolidate, then autograde homework submissions in the SRC dir, sending results to the DEST dir'
#         parser_ag = subparsers.add_parser('autograde',
#                                           aliases=['a'],
#                                           parents=[parser_src],
#                                           help=szSummary,
#                                           description=szHelp)
#         parser_ag.add_argument('-g', '--GenerateGradesheet', action='store_true',
#                                help='generate a blank gradesheet, suitable for manual grading (currently only supported by Javascript assignments)')
#         parser_ag.set_defaults(func=fnPrepAutograde)
#
#         szHelp = 'Consolidate homework submissions in the SRC dir'
#         szSummary = szHelp
#         parser_consolidator = subparsers.add_parser('consolidate',
#                                                     aliases=['o'],
#                                                     parents=[parser_src],
#                                                     help=szSummary,
#                                                     description=szHelp)
#         parser_consolidator.set_defaults(func=fnPrepConsolidate)
#
#         szSummary = 'Copy feedback files and rename them to match new revision name'
#         szHelp = 'Copy feedback files from SRC to DEST and rename them to match new revision name'
#         parser_copy_revision_feedback = subparsers.add_parser('CopyRevisionFeedback',
#                                                               aliases=['r'],
#                                                               parents=[parser_src_dest],
#                                                               help=szSummary,
#                                                               description=szHelp)
#
#         parser_copy_revision_feedback.set_defaults(func=fnPrepCopyRevisionFeedback)
#
#
#
#         szSummary = 'Copy feedback files and rename them to match new revision name'
#         szHelp = 'Copy feedback files from SRC to DEST and rename them to match new revision name'
#         parser_copy_revision_feedback = subparsers.add_parser('CopyRevisionFeedback',
#                                                               aliases=['r'],
#                                                               parents=[parser_src_dest],
#                                                               help=szSummary,
#                                                               description=szHelp)
#
#         parser_copy_revision_feedback.set_defaults(func=fnPrepCopyRevisionFeedback)
#
#         szSummary = 'Copy template file to all student subdirectories'
#         szHelp = 'Copy template file (given by SRC) to all student subdirectories in DEST (rename files to match subdir and put subdir into first line of word .DOC)'
#         parser_copy_template = subparsers.add_parser('CopyTemplateToStudents',
#                                                      aliases=['t'],
#                                                      parents=[parser_src_dest],
#                                                      help=szSummary,
#                                                      description=szHelp)
#         parser_copy_template.add_argument('-p', '--prefix',
#                                           help='Optional string value to prefix template with')
#         parser_copy_template.set_defaults(func=fnPrepCopyTemplate)
#
#     # we're not installing the StudentTracker parsers anymore
#     # this is the end of an era, man :(....
#
# #endregion
#     if len(sys.argv) == 1:
#         root_parser.print_help()
#         sys.exit(0)
#
#     args = root_parser.parse_args()
#
#     # set up defaults for common command line args
#     setattr(args, 'SRC', getattr(args, 'SRC', None))
#     setattr(args, 'DEST', getattr(args, 'DEST', None))
#     setattr(args, 'EXAM', getattr(args, 'EXAM', None))
#     setattr(args, 'prefix', getattr(args, 'prefix', None))
#     setattr(args, 'verbose', getattr(args, 'verbose', False))
#
#     # Only pre-process first positional arg if we know that we'll need file paths:
#     if args.func != fnPrepExamGen \
#         and args.SRC is not None:
#         args.SRC = os.path.abspath(args.SRC)
#
#     if args.DEST is not None:
#         args.DEST = os.path.abspath(args.DEST)
#
#     # give optional args default values as needed:
#     if args.prefix is None:
#         args.prefix = ""
#
#     # Would like to allow for multiple levels of verbosity, if needed
#     # for right now the command-line flag is just T/F, so
#     # we'll translate into an int here:
#     if args.verbose is True:
#         args.verbose = 1
#     else:
#         args.verbose = 0
#
#     try:
#         # call / dispatch out to the function that handles the menu item
#         args.func(args)
#     except GradingToolError as ex:
#         printError(str(ex))
#         #raise
#         sys.exit(-1)
#
#
#
if __name__ == "__main__":
    # file_to_parse = """C:\MikesStuff\Pers\Dropbox\Personal\Finance, Insurance, Etc\Downloads\Venmo\\05-19-2022.pdf"""
    file_to_parse = """C:\MikesStuff\Pers\Dropbox\Personal\Finance, Insurance, Etc\Downloads\Venmo\\02-16-2022.pdf"""
    output_file = """C:\MikesStuff\Pers\Dropbox\Personal\Finance, Insurance, Etc\Downloads\Venmo\\02-16-2022.csv"""
    ConvertVenmoStatement(file_to_parse, output_file)
    # CLI()
