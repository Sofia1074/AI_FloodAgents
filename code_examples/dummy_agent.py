import spade

class DummyAgent(spade.agent.Agent):
    async def setup(self):
        print("Hello World! I'm agent {}".format(str(self.jid)))

async def main():
    dummy = DummyAgent("dummy@localhost", "your_password")
    await dummy.start()

if __name__ == "__main__":
    spade.run(main(), embedded_xmpp_server=True)