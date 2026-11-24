from aiapp.testing import AppTest


class Sources(AppTest):
    def test_answers_from_the_local_folder_with_a_citation(self):
        self.harness.wait_jobs()                                   # indexing
        self.models.reply("You have 30 days to return an item [1].", when="return")
        r = self.client.chat("How long do I have to return something?")
        self.assertIn("30 days", r.text)
        self.assertEqual(r.citations[0]["source"], "returns.md")
        self.assertIn("within 30 days of delivery", self.models.last.system)   # the passage reached the model
