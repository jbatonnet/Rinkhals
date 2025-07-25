import sys
import re
import os


def readSections(path, hintPath = None):

    if os.path.isabs(path):
        pass
    elif hintPath and os.path.isfile(correctedPath := os.path.join(hintPath, path)):
        path = correctedPath
    elif os.path.isfile(correctedPath := os.path.abspath(path)):
        path = correctedPath

    if not os.path.isfile(path):
        print(f'Could not find file "{path}", skipping contnet...')
        return []

    with open(path, 'r') as f:
        config = f.read()

    sections = re.findall("(?:^|\n)\[([^\]]+)\]((?:.|\n)*?)(?=\n\[|$)", config)

    i = 0
    while i < len(sections):
        sectionName = sections[i][0]
        if sectionName.startswith('include '):
            includePath = sectionName[8:].strip()
            includeSections = readSections(includePath, os.path.dirname(path))
            sections = sections[:i] + includeSections + sections[i + 1:]
            i -= 1
        i += 1

    return sections or []


def main():
    args = sys.argv

    sourceConfigFiles = args[1:]

    # Read all sections and resolve includes
    sections = []
    for sourceConfigFile in sourceConfigFiles:
        for section in readSections(sourceConfigFile):
            sections.append(section)

    # Decode sections content
    sections = [ ( s[0], re.findall('(?:^|\n)([^\[\]\s:]+[^\[\]:]+):((?:.|\n)*?)(?=\n[^\[\]\s#:]|\n\[|$)', s[1]) ) for s in sections ]

    # Resolve section overrides
    resolvedSections = {}
    for section in sections:
        sectionName = section[0]
        sectionContent = section[1]

        #if sectionName.startswith('#'):
        #    continue

        if sectionName.startswith('!'):
            sectionName = sectionName[1:]
            if sectionName in resolvedSections:
                resolvedSections.pop(sectionName)
            continue

        if not sectionName in resolvedSections:
            resolvedSections[sectionName] = {}

        for key, value in sectionContent:
            #if key.lstrip().startswith('#'):
            #    continue
            
            # normalize key by stripping leading/trailing whitespace to avoid
            # duplicates caused by spacing before the colon
            key = key.strip()

            if key.startswith('!'):
                key = key[1:].strip()
                if key in resolvedSections[sectionName]:
                    resolvedSections[sectionName].pop(key)
                continue

            resolvedSections[sectionName][key] = value

    # Write resolved sections to destination file
    print('# This file is generated automatically on every Rinkhals startup')
    print('# To modify its content, please use the printer.custom.cfg instead')
    print('')

    for name, content in resolvedSections.items():
        print(f'[{name}]')
        for key, value in content.items():
            print(f'{key}:{value}')
        print('')

    
if __name__ == "__main__":
    main()
