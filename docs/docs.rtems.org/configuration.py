#
# RTEMS Project Documentation
#

import datetime
import os
import xml.dom.minidom as xml

try:
    import configparser
except:
    import ConfigParser as configparser

def today():
    now = datetime.date.today()
    m = now.strftime('%b')
    y = now.strftime('%Y')
    if now.day == 11:
        s = 'th'
    elif now.day % 10 == 1:
        s = 'st'
    elif now.day == 12:
        s = 'th'
    elif now.day % 10 == 2:
        s = 'nd'
    elif now.day == 13:
        s = 'th'
    elif now.day == 3:
        s = 'rd'
    else:
        s = 'th'
    d = '%2d%s' % (now.day, s)
    return '%s %s %s' % (d, m, y)

class configuration:
    def __init__(self, ctx, config):
        self.ctx = ctx
        self.config = None
        self.branches = None
        self.releases = None
        self.titles = None
        self.name = None
        self.load(config)

    def __str__(self):
        import pprint
        s = self.name + os.linesep
        s += 'Titles:' + os.linesep + \
             pprint.pformat(self.titles, indent = 1, width = 80) + os.linesep
        s += 'Branches:' + os.linesep + \
             pprint.pformat(self.branches, indent = 1, width = 80) + os.linesep
        s += 'Releases:' + os.linesep + \
             pprint.pformat(self.releases, indent = 1, width = 80) + os.linesep
        s += 'Legacy:' + os.linesep + \
             pprint.pformat(self.get_legacy_releases(), indent = 1, width = 80) + os.linesep
        return s

    def _get_item(self, section, label, err = True):
        try:
            rec = self.config.get(section, label).replace(os.linesep, ' ')
            return rec
        except:
            if err:
                self.ctx.fatal('config: no %s found in %s' % (label, section))
        return None

    def _get_items(self, section, err = True):
        try:
            items = self.config.items(section)
            return items
        except:
            if err:
                self.ctx.fatal('config: section %s not found' % (section))
        return []

    def _comma_list(self, section, label, error = True, sort = False):
        items = self._get_item(section, label, error)
        if items is None:
            return []
        items = [a.strip() for a in items.split(',')]
        if sort:
            return sorted(set(items))
        else:
            return items

    def _xml_create_doc(self, cat, name, legacy, release, html, pdf):
        doc = cat.createElement('doc')

        name_ = cat.createElement('name')
        text = cat.createTextNode(name)
        name_.appendChild(text)
        doc.appendChild(name_)

        title_ = cat.createElement('title')
        text = cat.createTextNode(self.titles[name.lower()])
        title_.appendChild(text)
        doc.appendChild(title_)

        if legacy:
            legacy_ = cat.createElement('legacy')
            text = cat.createTextNode('Yes')
            legacy_.appendChild(text)
            doc.appendChild(legacy_)

        release_ = cat.createElement('release')
        text = cat.createTextNode(release)
        release_.appendChild(text)
        doc.appendChild(release_)

        version_ = cat.createElement('version')
        text = cat.createTextNode(release)
        version_.appendChild(text)
        doc.appendChild(version_)

        html_ = cat.createElement('html')
        text = cat.createTextNode(html)
        html_.appendChild(text)
        doc.appendChild(html_)

        pdf_ = cat.createElement('pdf')
        text = cat.createTextNode(pdf)
        pdf_.appendChild(text)
        doc.appendChild(pdf_)

        return doc

    def load(self,  name):
        '''Load the configuration INI file. Create titles, branches, and releases.'''
        self.name = name
        self.config = configparser.ConfigParser()
        try:
            self.config.read(self.name)
        except configparser.ParsingError as ce:
            self.ctx.fatal('config: %s' % (ce))
        self.titles = {}
        for t in self._get_items('titles'):
            title = t[1]
            if title[0] == '"':
                title = title[1:]
            if title[-1] == '"':
                title = title[:-1]
            self.titles[t[0]] = title
        self.latestes = {}
        for l in self._get_items('latest'):
            self.latestes[l[0]] = l[1]
        self.branches = self._get_items('branches')
        self.releases = {}
        self.releases['releases'] = self._get_items('releases')
        for r in self.releases['releases']:
            label = r[1]
            self.releases[label] = {}
            rel = self.releases[label]
            template = self._get_item(label, 'template', False)
            if template is None:
                template = label
            rel['legacy'] = self._get_item(template, 'legacy', False)
            if rel['legacy'] is None:
                rel['legacy'] = self._get_item(label, 'legacy', False)
            if rel['legacy'] == 'yes':
                rel['manuals'] = self._comma_list(template, 'manuals')
                rel['supplements'] = self._comma_list(template, 'supplements', False)
                rel['index_per_doc'] = self._get_item(template, 'index_per_doc', False)
                if rel['index_per_doc'] is None:
                    rel['index_per_doc'] = self._get_item(label, 'index_per_doc', False)
                rel['html'] = self._get_item(label, 'html')
                rel['pdf'] = self._get_item(label, 'pdf')
                rel['date'] = self._get_item(label, 'date')
                for d in rel['manuals'] + rel['supplements']:
                    if d.lower() not in self.titles:
                        self.ctx.fatal('title not found in %s: %s' % (label, d))
            else:
                rel['doxygen'] = self._get_item(template, 'doxygen', False)
                if rel['doxygen'] is None:
                    rel['doxygen'] = 'no'

    def get_release(self, release):
        if self.releases is None:
            self.ctx.fatal('no configuration loaded')
        for r in self.releases['releases']:
            if r[0] == release:
                return r[0], r[1], self.releases[r[1]]
        self.ctx.fatal('cannot find release: %s' % (release))

    def is_legacy_release(self, release):
        if self.releases is None:
            self.ctx.fatal('no configuration loaded')
        name, label, rel = self.get_release(release)
        return rel['legacy'] == 'yes'

    def is_doxygen_release(self, release):
        if self.releases is None:
            self.ctx.fatal('no configuration loaded')
        name, label, rel = self.get_release(release)
        if not 'doxygen' in rel:
            return False
        return rel['doxygen'] == 'yes'

    def get_legacy_releases(self):
        if self.releases is None:
            self.ctx.fatal('no configuration loaded')
        return sorted([r[0] for r in self.releases['releases'] if self.releases[r[1]]['legacy'] == 'yes'])

    def get_releases(self):
        if self.releases is None:
            self.ctx.fatal('no configuration loaded')
        return sorted([r[0] for r in self.releases['releases']])

    def generate_xml(self):
        if self.releases is None:
            self.ctx.fatal('no configuration loaded')
        for r in self.get_legacy_releases():
            name, label, rel = self.get_release(r)

            cat = xml.Document()

            root = cat.createElement('rtems-docs')
            root.setAttribute('date', rel['date'])
            cat.appendChild(root)

            heading = cat.createElement('catalogue')
            text = cat.createTextNode(name)
            heading.appendChild(text)
            root.appendChild(heading)

            for m in rel['manuals']:
                if 'index_per_doc' in rel:
                    html = rel['html'] + '/' + m + '/index.html'
                else:
                    html = rel['html'] + '/' + m + '.html'
                pdf = rel['pdf'] + '/' + m + '.pdf'
                legacy = rel['legacy']
                doc = self._xml_create_doc(cat, m, legacy, name, html, pdf)
                root.appendChild(doc)

            catnode = self.ctx.get_cwd().make_node('%s.xml' % (name))
            catnode.write(cat.toprettyxml(indent = ' ' * 2, newl = os.linesep))

    def generate_html(self, what, indent = 5):
        def _tag(tag):
            for c in [' ','.',',','(','}','[',']']:
                tag = tag.replace(c, '_')
            return tag

        def _branch_tag(branch):
            return _tag(branch[0])
        def _branch_script(branch):
            path = branch[1]
            tag = _branch_tag(branch)
            return \
                '<script> loadCatalogue("branches/%s/catalogue.xml", "branches/%s", "%s", true, false); </script>\n' \
                % (path, path, tag)

        def _release_tag(release):
            return _tag(release[0])
        def _release_script(release):
            name = release[0]
            label = release[1]
            tag = _release_tag(release)
            if self.is_legacy_release(name):
                catalogue = "releases/%s.xml" % (name)
                path = 'releases'
            else:
                catalogue = "releases/%s/catalogue.xml" % (label)
                path = 'releases/%s' % (label)
            if self.is_doxygen_release(name):
                doxygen = "true"
            else:
                doxygen = "false"
            return \
                '<script> loadCatalogue("%s", "%s", "%s", %s, false); </script>\n' \
                % (catalogue, path, tag, doxygen)

        def _match_all(tag):
            return True
        def _match_latest_release(tag):
            return tag == _tag(self.latest('release'))

        if self.releases is None:
            self.ctx.fatal('no configuration loaded')

        if what == 'branches':
            data = self.branches
            tagger = _branch_tag
            scripter = _branch_script
            matcher = _match_all
        elif what == 'releases':
            data = self.releases['releases']
            tagger = _release_tag
            scripter = _release_script
            matcher = _match_all
        elif what == 'latest-release':
            data = self.releases['releases']
            tagger = _release_tag
            scripter = _release_script
            matcher = _match_latest_release
        else:
            self.ctx.fatal('invalid html type: ' + what)

        scripts = ''
        hindent = ' ' * indent
        html = ''

        for d in data:
            tag = tagger(d)
            if matcher(tag):
                html += hindent + '<div id="rtems-catalogue-%s">\n' % (tag)
                html += hindent + ' <b>%s</b> No catalogue found.\n' % (d[0])
                html += hindent + '</div>\n'
                scripts += ' ' * 3 + scripter(d)

        html = html[:-1]
        scripts = scripts[:-1]
        return html, scripts

    def latest(self, what):
        if what not in self.latestes:
            self.ctx.fatal(what + 'not found in latest')
        return self.latestes[what]
