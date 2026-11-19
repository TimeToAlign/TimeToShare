/**
 * The part of jsonld.js the RDF tests call. The package ships no type
 * declarations; this one states the options the tests pass.
 */
declare module "jsonld" {
  /** A document loader that may refuse every URL by throwing. */
  type DocumentLoader = (url: string) => Promise<never>;

  interface CanonizeOptions {
    /** The base IRI relative references resolve against. */
    readonly base: string;
    /** Whether a key that expands to nothing is an error; false drops it. */
    readonly safe: boolean;
    readonly documentLoader: DocumentLoader;
    readonly format: "application/n-quads";
    readonly canonizeOptions: { readonly algorithm: "RDFC-1.0" };
  }

  const jsonld: {
    /** The canonical N-Quads of a JSON-LD document's dataset (RDFC-1.0). */
    canonize(input: unknown, options: CanonizeOptions): Promise<string>;
  };
  export default jsonld;
}
