using System.Text.Json.Serialization;

namespace RFP_Blazor_Frontend.Models
{
        public class SelectRfpResponse
        {
            [JsonPropertyName("name")]
            public string? Name { get; set; }
        }
}
