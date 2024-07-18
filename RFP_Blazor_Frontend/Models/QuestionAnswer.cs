namespace RFP_Blazor_Frontend.Models
{
    public class QuestionAnswer
    {
        public string Question { get; set; }
        public string Answer { get; set; }

        public QuestionAnswer(string question, string answer)
        {
            Question = question;
            Answer = answer;
        }
    }
}
