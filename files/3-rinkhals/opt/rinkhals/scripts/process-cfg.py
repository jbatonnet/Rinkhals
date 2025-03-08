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

    sections = re.findall("\[([^\]]+)\]((?:.|\n)*?)(?=\n\[|$)", config)

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
    if len(args) != 3:
        print(f'Error: {args[0]} needs 2 arguments, source and destination config path')

    sourceConfigPath = args[1]
    destinationConfigPath = args[2]

    # Read all sections and resolve includes
    sections = readSections(sourceConfigPath)

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

            if key.startswith('!'):
                key = key[1:]
                if key in resolvedSections[sectionName]:
                    resolvedSections[sectionName].pop(key)
                continue

            resolvedSections[sectionName][key.lstrip()] = value

    # Write resolved sections to destination file
    with open(destinationConfigPath, 'w') as f:
        f.write('# This file is generated automatically on every Rinkhals startup\n')
        f.write('# To modify its content, please use the printer.custom.cfg instead\n')
        f.write('\n')

        for name, content in resolvedSections.items():
            f.write(f'[{name}]\n')
            for key, value in content.items():
                f.write(f'{key}:{value}\n')
            f.write('\n')

    
if __name__ == "__main__":
    main()
