# generation B option class


class _Parser:
    def __init__(self, args, shortopts):
        self.args = list(args)
        self.shortopts = shortopts

    def parse(self):
        options = []
        index = 0

        while index < len(self.args):
            argument = self.args[index]
            if argument == "--":
                return options, self.args[index + 1:]
            if argument == "-" or not argument.startswith("-"):
                return options, self.args[index:]

            letters = argument[1:]
            position = 0
            while position < len(letters):
                letter = letters[position]
                option_index = self.shortopts.find(letter)
                if option_index < 0 or letter == ":":
                    raise ValueError("option -%s not recognized" % letter)

                takes_value = (
                    option_index + 1 < len(self.shortopts)
                    and self.shortopts[option_index + 1] == ":"
                )
                if takes_value:
                    if position + 1 < len(letters):
                        value = letters[position + 1:]
                    else:
                        index += 1
                        if index >= len(self.args):
                            raise ValueError("option -%s requires argument" % letter)
                        value = self.args[index]
                    options.append(("-" + letter, value))
                    break

                options.append(("-" + letter, ""))
                position += 1

            index += 1

        return options, []


def getopt(args, shortopts):
    return _Parser(args, shortopts).parse()
