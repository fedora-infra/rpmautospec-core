## START: Set by rpmautospec
## (rpmautospec version 0.3.8)
## RPMAUTOSPEC: autorelease, autochangelog
%define autorelease(e:s:pb:n) %{?-p:0.}%{lua:
    release_number = 7;
    base_release_number = tonumber(rpm.expand("%{?-b*}%{!?-b:1}"));
    print(release_number + base_release_number - 1);
}%{?-e:.%{-e*}}%{?-s:.%{-s*}}%{!?-n:%{?dist}}
## END: Set by rpmautospec

# Our dummy-test-packages are named after canary varieties, meet Gloster, Rubino and Crested
# Source: https://www.omlet.co.uk/guide/finches_and_canaries/canary/canary_varieties
Name:           dummy-test-package-gloster

Version:        0
Release:        %{autorelease}
Summary:        Dummy Test Package called Gloster
License:        MIT
URL:            http://fedoraproject.org/wiki/DummyTestPackages

# The tarball contains a file with an uuid to test later and a LICENSE
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

%description
This is a dummy test package for the purposes of testing if the Fedora CI
pipeline is working. There is nothing useful here.

%prep
%autosetup

%build
# nothing to do

%install
mkdir -p %{buildroot}%{_datadir}
cp -p uuid %{buildroot}%{_datadir}/%{name}

%files
%license LICENSE
%{_datadir}/%{name}

%changelog
* Fri Mar 27 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-7
- Undo vandalism
- Change license to MIT

* Fri Mar 27 2020 King ISØ-8859 <kingiso8859@example.com> - 0-7
- Honour the tradition of antiquated encodings!

* Fri Mar 27 2020 Nils Philippsen <nils@redhat.com> - 0-6
- Convert to automatic release and changelog

* Tue Jan 21 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-5
- rebuilt

* Thu Jan 16 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-4
- rebuilt

* Fri Jan 10 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-3
- rebuilt

* Fri Jan 10 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-2
- rebuilt

* Thu Dec 19 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-1
- Initial packaging work
