using System.Text.Json.Serialization;

namespace RFP_Blazor_Frontend.Models
{
    public class ChatResponse
    {
        [JsonPropertyName("ai_response")]
        public string? AiResponse { get; set; }

        [JsonPropertyName("function")]
        public string? Function { get; set; }
    }
}


