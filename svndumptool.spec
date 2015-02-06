%define name svndumptool
%define version 0.8.0
%define release 0pre1

Summary: Package and cmdline tool for processing Subversion dump files.
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: GNU General Public License (GPL)
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Martin Furter <mf@rola.ch>
Url: http://svn.borg.ch/svndumptool/

%description
SvnDumpTool is a tool for processing Subversion dump files. It's written in
python.

%prep
%setup

%build
python setup.py build

%install
python setup.py install --optimize=1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
/usr/bin/svndumptool.pyc
/usr/bin/svndumptool.pyo
