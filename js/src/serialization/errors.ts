/**
 * The errors of the readers: a text the reading rules refuse, with the
 * position of the fault.
 */

/** The line and column, both counted from 1, of an offset in a text; a line ends at each `\n`. */
export function positionOf(text: string, offset: number): { line: number; column: number } {
  const lines = text.slice(0, offset).split("\n");
  return { line: lines.length, column: (lines.at(-1) as string).length + 1 };
}

/**
 * A text the reading rules refuse, and where: `offset` counts UTF-16 code
 * units from 0, `line` and `column` count from 1, the column in UTF-16 code
 * units. A `SyntaxError`, so a caller catching `SyntaxError` catches it.
 */
abstract class TextSyntaxError extends SyntaxError {
  readonly offset: number;
  readonly line: number;
  readonly column: number;

  constructor(language: string, reason: string, text: string, offset: number) {
    const { line, column } = positionOf(text, offset);
    super(`${reason} at line ${line}, column ${column} of the ${language} text`);
    this.offset = offset;
    this.line = line;
    this.column = column;
  }
}

/** A text read as JSON that the reading rules refuse. */
export class JsonSyntaxError extends TextSyntaxError {
  constructor(reason: string, text: string, offset: number) {
    super("JSON", reason, text, offset);
    this.name = "JsonSyntaxError";
  }
}

/** A text read as YAML that the reading rules refuse. */
export class YamlSyntaxError extends TextSyntaxError {
  constructor(reason: string, text: string, offset: number) {
    super("YAML", reason, text, offset);
    this.name = "YamlSyntaxError";
  }
}
