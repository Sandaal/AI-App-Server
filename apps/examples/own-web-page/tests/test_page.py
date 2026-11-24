from aiapp.testing import AppTest


class Page(AppTest):
    def test_page_is_served(self):
        r = self.client.get("/")
        self.assertEqual(r.status, 200)
        self.assertIn("<aiapp-chat", r.text)

    def test_own_route(self):
        self.assertIn("tip", self.client.post("/tip").json())

    def test_chat_box_route(self):
        self.harness.wait_jobs()
        self.models.reply("You have 30 days [1].", when="return")
        self.assertIn("30 days", self.client.chat("How long do I have to return an item?").text)
