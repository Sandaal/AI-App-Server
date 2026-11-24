from aiapp.testing import AppTest


class Guards(AppTest):
    def test_normal_question(self):
        self.models.reply("The X200 has a 2-year warranty.")
        r = self.client.post("/ask", {"question": "What is the warranty on the X200?"})
        self.assertEqual(r.status, 200)
        self.assertIn("2-year", r.text)

    def test_competitor_in_the_question_is_blocked(self):
        r = self.client.post("/ask", {"question": "Is Fabrikam cheaper?"})
        self.assertEqual(r.status, 400)
        self.assertIn("only talk about Contoso", r.text)
        self.assertEqual(self.models.calls, [])            # the model was never called

    def test_competitor_in_the_answer_is_blocked(self):
        self.models.reply("Northwind sells a similar one.")
        r = self.client.post("/ask", {"question": "Any alternatives?"})
        self.assertIn("only talk about Contoso", r.text)

    def test_personal_data_in_answers_is_redacted(self):
        self.models.reply("Write to sales@contoso.com.")
        r = self.client.post("/ask", {"question": "How do I contact sales?"})
        self.assertIn("[EMAIL]", r.text)
        self.assertNotIn("sales@contoso.com", r.text)
