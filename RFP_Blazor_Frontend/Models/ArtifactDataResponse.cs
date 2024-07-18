using System.Text.Json.Serialization;

namespace RFP_Blazor_Frontend.Models
{
    public class ArtifactDataResponse
    {
        [JsonPropertyName("details")]
        public string? Details { get; set; }
    }
}

