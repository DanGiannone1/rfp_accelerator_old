using System.Text.Json.Serialization;

namespace RFP_Blazor_Frontend.Models
{
    public class SelectRfpRequest
    {
        [JsonPropertyName("rfpId")]
        public string? RfpId { get; set; }
    }

}
