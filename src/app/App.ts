import { AppController } from "@/app/appController";

export class App {
  private readonly controller = new AppController();

  async init(): Promise<void> {
    await this.controller.init();
  }
}
