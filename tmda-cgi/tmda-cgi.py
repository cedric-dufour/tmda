#!/usr/bin/env python
#
# Copyright (C) 2002 Gre7g Luterman <gre7g@wolfhome.com>
#
# This file is part of TMDA.
#
# TMDA is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.  A copy of this license should
# be included in the file COPYING.
#
# TMDA is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with TMDA; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"Web interface to TMDA tools."

import cgi
import os
import sys

# Pick up the TMDA and TMDA/pythonlib directories to get any overrides of
# standard modules and packages.  Note that these must go at the very front of
# the path for this reason.
sys.path.insert(0, os.environ["TMDA_BASE_DIR"])
sys.path.insert(0, os.path.join(os.environ["TMDA_BASE_DIR"], "TMDA",
  "pythonlib"))
from TMDA import Errors

import CgiUtil
import MyCgiTb
import Session
import Template

def Call(Library, Str = None):
  "Launch a library with the appropriate globals."
  Library.Form  = Form
  Library.PVars = PVars
  if Str:
    Library.Show(Str)
  else:
    Library.Show()

# Prepare the traceback in case of uncaught exception
MyCgiTb.Content()
MyCgiTb.ErrTemplate = "prog_err2.html"

# Make some global stuff available to all
Template.Template.BaseDir = "%s/display/themes/Blue/template" % \
  os.path.abspath(os.path.split(sys.argv[0])[0])
Template.Template.Dict["Script"]   = os.environ["SCRIPT_NAME"]
Template.Template.Dict["SID"]      = ""
Template.Template.Dict["DispDir"]  = os.environ["TMDA_CGI_DISP_DIR"]
Template.Template.Dict["ThemeDir"] = "%s/themes/Blue" % \
  os.environ["TMDA_CGI_DISP_DIR"]
Template.Template.Dict["ErrMsg"]   = "No error message returned.  Sorry!"

# Check version information
try:
  import Version
  Version.Test()
except ImportError, ErrStr:
  CgiUtil.TermError("Failed to import TMDA module.", ErrStr, "import TMDA", "",
    "Upgrade to the most recent release of TMDA.")

# Process any CGI fields
Form = cgi.FieldStorage()

# Get any persistent variables
try:
  try:
    PVars = Session.Session(Form)
    CgiUtil.ErrTemplate = "error.html"
  except CgiUtil.NotInstalled, (ErrStr, PVars):
    Template.Template.Dict["ErrMsg"] = ErrStr
    # Can log in but TMDA is not installed correctly
    if ErrStr[0].find("must be chmod 400 or 600") < 0:
      # Serious error.  Suggest an install
      import Install
      Call(Install)
      sys.exit()
    else:
      CgiUtil.TermError("crypt_key permissions.", "Bad permissions.",
        "reading crypt_key", ErrStr, "Fix permissions on crypt_key.")
except CgiUtil.JustLoggedIn, (ErrStr, PVars):
  PVars["Pager"]       = 0
  PVars["InProcess"]   = {}
  PVars["LocalConfig"] = "Form"
  PVars.Save()

# Share "globals"
CgiUtil.PVars = PVars

# First visit to any page?
if not Form.keys():
  # Release an e-mail by URL?
  try:
    if os.environ["QUERY_STRING"]:
      import Release
      Release.Release(os.environ["QUERY_STRING"])
      sys.exit()
  except KeyError:
    pass
  # Initial login
  import Login
  Call(Login)

# Logged in yet?
elif not PVars.Valid:
  import Login
  if Form.has_key("cmd") and (Form["cmd"].value != "logout"):
    Call(Login, "Wrong password.")
  else:
    Call(Login)

elif Form.has_key("cmd"):

  Cmd = Form["cmd"].value
  if Cmd == "init":
    Cmd = PVars[("Login", "InitPage")]

  # View?
  if Cmd in ("incoming", "outgoing"):
    import EditFilter
    Call(EditFilter)
  elif Cmd[:8] == "editlist":
    import EditList
    Call(EditList)
  elif Cmd == "gen_addr":
    import GenAddr
    Call(GenAddr)
  elif Cmd == "globalconfig":
    import GlobalConfig
    Call(GlobalConfig)
  elif Cmd == "info":
    import Info
    Call(Info)
  elif Cmd == "install":
    pass
  elif Cmd == "localconfig":
    import LocalConfig
    Call(LocalConfig)
  elif Cmd == "pending":
    import PendList
    Call(PendList)
  elif Cmd == "restore":
    pass
  elif Cmd == "uninstall":
    import Install
    Call(Install)
  elif Cmd == "view":
    import View
    try:
      Call(View)
    except Errors.MessageError:  # No messages left?
      import PendList
      Call(PendList)
  elif Cmd == "test_addr":
    import TestAddr
    Call(TestAddr)
  elif Cmd == "theme":
    import Theme
    Call(Theme)
  else:
    CgiUtil.TermError("Command not recognized.", "Unknown command: %s" %
      Cmd, "interpret command", "", "Please be patient while we release newer "
      "versions of the code which will implement this function.")

else:
  CgiUtil.TermError("No command instruction.", "Program bug.",
    "interpret command", "", "Please contact the programmers and let them "
    "know what you did to reach this message.")
