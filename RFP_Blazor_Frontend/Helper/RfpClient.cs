using Microsoft.AspNetCore.Components.Forms;
using RFP_Blazor_Frontend.Models;
using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace RFP_Blazor_Frontend.Helper;
public class RfpClient
{
    private readonly HttpClient _httpClient;
    private string _selectedRFP = string.Empty;
    public List<string>? ListOfRfps { get; set; }
    public string SelectedRFP { 
        get
        {
            return _selectedRFP;
        }
        set
        {
            _selectedRFP = value;
        } 
    }
    public bool NewUpload { get; set; } 

    public RfpClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
        _httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
    }

    public async Task<List<string>> GetRfpsAsync()
    {
        var response = await _httpClient.GetAsync("/rfps");
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync();
        ListOfRfps = JsonSerializer.Deserialize<List<string>>(content) ?? new List<string>();
        // return JsonSerializer.Deserialize<List<string>>(content) ?? new List<string>();
        return ListOfRfps;
    }

    public async Task<string> GetStatusAsync()
    {
        var response = await _httpClient.GetAsync("/status");
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync();
        return content ?? string.Empty;
    }

    public async Task<string> SelectRfpAsync(string rfpId)
    {
        var payload = new SelectRfpRequest { RfpId = rfpId };
        var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync("/select-rfp", content);
        response.EnsureSuccessStatusCode();

        var responseContent = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<SelectRfpResponse>(responseContent);
        return result?.Name ?? string.Empty; ;
    }

    public async Task<HttpResponseMessage> UploadFileAsync(string filePath, IBrowserFile file)
    {

        var fileContent = new ByteArrayContent(File.ReadAllBytes(filePath));
        fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("application/pdf");

        var formData = new MultipartFormDataContent();
        formData.Add(fileContent, "file", Path.GetFileName(filePath));

        return await _httpClient.PostAsync("/upload", formData);
    }

    public async Task<HttpResponseMessage> UploadFileAsync2(IBrowserFile file)
    {
        try
        {
            // Read stream from IBrowserFile
            // replace spaces in filename with _ 
            var filename = file.Name.Replace(" ", "_");
            using (var stream = file.OpenReadStream(maxAllowedSize: 10485760))
            {
                var fileContent = new StreamContent(stream);
                fileContent.Headers.ContentType = new MediaTypeHeaderValue(file.ContentType);

                var formData = new MultipartFormDataContent();
                formData.Add(fileContent, "file", filename);
                NewUpload = true;
                return await _httpClient.PostAsync("/uploadtoblob", formData);
            }
            
        }
        catch (Exception ex)
        {
            // Handle exception as needed
            NewUpload = false;  
            Console.WriteLine($"Error uploading file: {ex.Message}");
            throw;
        }
    }

    // Call Chat Completion Endpoint without streaming...
    public async Task<string> ChatAsync(string message)
    {
        var payload = new ChatRequest { Message = message };
        var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync("/chat", content);
        response.EnsureSuccessStatusCode();

        var responseContent = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<ChatResponse>(responseContent);
        return result?.AiResponse ?? string.Empty;
    }

    public async IAsyncEnumerable<string> ChatStreamAsync(string message)
    {
        var payload = new ChatRequest { Message = message };
        var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        var baseAddress = _httpClient.BaseAddress ?? throw new InvalidOperationException("BaseAddress is not set on HttpClient.");

        var request = new HttpRequestMessage
        {
            Method = HttpMethod.Post,
            RequestUri = new Uri(baseAddress, "/stream_chat"),
            Content = content
        };

        var response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);
        var responseStreamTesting = await response.Content.ReadAsStreamAsync();

        if (response.IsSuccessStatusCode)
        {
            using var responseStream = await response.Content.ReadAsStreamAsync();
            using var reader = new StreamReader(responseStream);
            char[] buffer = new char[8192];
            int charsRead;
            while ((charsRead = await reader.ReadAsync(buffer, 0, buffer.Length)) > 0)
            {
                yield return new string(buffer, 0, charsRead);
            }
        }
        else
        {
            Console.WriteLine($"Server response code: {response.StatusCode}");
            yield return "";
        }
    }

    public async Task<string> GetArtifactDataAsync(string artifactType)
    {
        var response = await _httpClient.GetAsync($"/artifact-data?artifactType={artifactType}");
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<ArtifactDataResponse>(content);
        return result?.Details ?? string.Empty;
    }

    public async Task<List<string>> GetArtifactsAsync()
    {
        var response = await _httpClient.GetAsync("/artifacts");
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<List<string>>(content) ?? new List<string>();
    }
}
