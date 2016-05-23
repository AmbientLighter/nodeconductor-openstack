Name: nodeconductor-openstack
Summary: OpenStack plugin for NodeConductor
Group: Development/Libraries
Version: 0.2.0
Release: 1.el7
License: Copyright 2016 OpenNode LLC. All rights reserved.
Url: http://nodeconductor.com
Source0: %{name}-%{version}.tar.gz

Requires: nodeconductor >= 0.97.0
Requires: python-ceilometerclient = 2.0.1
Requires: python-cinderclient = 1.5.0
Requires: python-glanceclient = 1.1.1
Requires: python-iptools >= 0.6.1
Requires: python-keystoneclient = 1.8.1
Requires: python-neutronclient = 4.0.0
Requires: python-novaclient = 2.35.0

BuildArch: noarch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

BuildRequires: python-setuptools


%description
OpenStack plugin for NodeConductor.

%prep
%setup -q -n %{name}-%{version}

%build
python setup.py build

%install
rm -rf %{buildroot}
python setup.py install --single-version-externally-managed -O1 --root=%{buildroot} --record=INSTALLED_FILES

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)

%changelog
* Mon May 16 2016 Jenkins <jenkins@opennodecloud.com> - 0.2.0-1.el7
- New upstream release

* Mon May 16 2016 Ilja Livenson <ilja@opennodecloud.com> - 0.1.0-1.el7
- Initial version of the package

