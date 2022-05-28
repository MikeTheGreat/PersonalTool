# '''
# Created on May 22, 2022
#
# Personal Tool (gt)
#
#
# @author: MikePanitz
#
# '''
### T O D O      L I S T ###############################################################################################
# TODO Venmo convert: prints xacts to screen if verbose setting is on?
# TODO Venmo convert: 'account name' CLI arg to put at the top of the file?

import argparse
import os
import sys

from colorama import init
init()

import stackprinter
stackprinter.set_excepthook(style='darkbg2')

from finance.venmo import ConvertVenmoStatement

# Utility for print()ing debug info:
# https://github.com/gruns/icecream
# # from icecream import install
# # install()

#region Functions to handle menu options
def fnConvertVenmoToCSV(args):
    print(
        f'\nConvert Venmo PDF statements to CSV files:\n\tSRC:\t{args.SRC}\n\tDEST:\t{args.DEST}\n')

    if not os.path.isfile(args.SRC):
        print("'SRC' argument must be a file but isn't")
        sys.exit()

    # do the conversion:
    ConvertVenmoStatement(args.SRC, args.DEST)

#endregion

def CLI():

#region Set up argparse
    root_parser = argparse.ArgumentParser(
        description='PersonalTool: Automate tasks for my personal life')

    subparsers = root_parser.add_subparsers(dest='command', help='sub-command help')

    parser_verbose = argparse.ArgumentParser(add_help=False)
    parser_verbose.add_argument('-v', '--verbose', action='store_true',
                                help='For additional, more detailed output')

    parser_src = argparse.ArgumentParser(add_help=False, parents=[parser_verbose])
    parser_src.add_argument('SRC', help='the source file/dir/etc')

    parser_src_dest = argparse.ArgumentParser(add_help=False, parents=[parser_src])
    parser_src_dest.add_argument('DEST', help='the destination file/dir/etc')

    szSummary: str
    szHelp: str


#region Venmo Utils
    ################################# Venmo Utils ################################################
    def setup_exam_gen_parsers(subparsers):
        szSummary = 'Venmo Utils'
        szHelp = 'Tools to deal with Venmo statements, etc'
        parser_exams = subparsers.add_parser('v',
                                                aliases=['v'],
                                                parents=[parser_verbose],
                                                help=szSummary,
                                                description=szHelp)

        venmo_subparsers = parser_exams.add_subparsers(dest='subcommand',
                                                                   help="Help for the Venmo utils")
        szSummary = 'Convert Venmo Statements (PDF to CSV)'
        szHelp = 'Read the Venmo monthly statement (a PDF, via SRC) and write the transactions to DEST (a CSV)'
        parser_exam_gen = venmo_subparsers.add_parser('convert_statement',
                                                aliases=['c'],
                                                parents=[parser_src_dest],
                                                help=szSummary,
                                                description=szHelp)
        parser_exam_gen.set_defaults(func=fnConvertVenmoToCSV)

    setup_exam_gen_parsers(subparsers)

#endregion

    if len(sys.argv) == 1:
        root_parser.print_help()
        sys.exit(0)

    args = root_parser.parse_args()

    # set up defaults for common command line args
    setattr(args, 'SRC', getattr(args, 'SRC', None))
    setattr(args, 'DEST', getattr(args, 'DEST', None))

    # Only pre-process first positional arg if we know that we'll need file paths:
    if args.SRC is not None:
        args.SRC = os.path.abspath(args.SRC)

    if args.DEST is not None:
        args.DEST = os.path.abspath(args.DEST)

    # Would like to allow for multiple levels of verbosity, if needed
    # for right now the command-line flag is just T/F, so
    # we'll translate into an int here:
    if args.verbose is True:
        args.verbose = 1
    else:
        args.verbose = 0

    # try:
    # call / dispatch out to the function that handles the menu item
    args.func(args)
    # except GradingToolError as ex:
    #     printError(str(ex))
    #     #raise
    #     sys.exit(-1)



if __name__ == "__main__":
    CLI()
