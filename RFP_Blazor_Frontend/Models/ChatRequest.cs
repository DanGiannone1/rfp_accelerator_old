using System.Text.Json.Serialization;

namespace RFP_Blazor_Frontend.Models
{
    public class ChatRequest
    {
        [JsonPropertyName("message")]
        public string? Message { get; set; }
    }
}


