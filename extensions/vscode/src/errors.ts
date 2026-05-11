export class NoviSentinelError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NoviSentinelError";
  }
}
