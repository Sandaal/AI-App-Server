from aiapp.testing import AppTest


class Routes(AppTest):
    def test_hello(self):
        r = self.client.post("/hello", {"name": "Ada"})
        self.assertEqual(r.json(), {"greeting": "Hello, Ada!"})
        self.assertEqual(self.client.post("/hello", {}).status, 400)

    def test_translate(self):
        self.models.reply("Bonjour")
        r = self.client.post("/translate", {"text": "Hello", "to": "French"})
        self.assertEqual(r.json()["translation"], "Bonjour")
        self.assertIn("French", self.models.last.system)

    def test_chat_remembers(self):
        self.models.reply("Nice to meet you, Ada.")
        self.client.chat("My name is Ada.", session="s1")
        self.models.reply("Your name is Ada.")
        r = self.client.chat("What is my name?", session="s1")
        self.assertIn("Ada", r.text)
        self.assertIn("My name is Ada.", str(self.models.last.messages))   # the history reached the model
